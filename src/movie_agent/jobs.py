"""Durable media submissions and local rendering, independent of conversation turns."""

import asyncio
import json
from dataclasses import asdict

import httpx

from .config import Binding
from .providers import MediaResult, Provider, ProviderError, data_url, download_media
from .store import now, uid


class Jobs:
    active_states = frozenset({"pending", "submitting", "queued", "running", "downloading", "rendering"})

    def __init__(self, store, config, media):
        self.store, self.config, self.media = store, config, media
        self.client = httpx.AsyncClient()
        self.tasks = {}
        self.notify = None
        self.gate = None
        self.closing = False
        self.loop = None
        self.semaphores = {"image": asyncio.Semaphore(4), "video": asyncio.Semaphore(2),
                           "audio": asyncio.Semaphore(3), "compose": asyncio.Semaphore(1)}

    async def start(self):
        for project in self.store.projects():
            for job in self.store.records(project["id"], "jobs"):
                if job["status"] == "failed" and job.get("result"):
                    self.store.update_record(job["id"], status="download_failed", failure_scope="retrieval")
                if job["status"] in {"submitting", "rendering"}:
                    if job["purpose"] == "compose":
                        self.store.update_record(job["id"], status="pending")
                    elif job.get("external_id"):
                        self.store.update_record(job["id"], status="queued")
                    else:
                        self.store.update_record(job["id"], status="unknown", error="进程在提交期间中断，需要核对外部任务")
        self.loop = asyncio.create_task(self._loop())

    async def close(self):
        self.closing = True
        if self.loop:
            self.loop.cancel()
        for task in self.tasks.values():
            task.cancel()
        await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)
        if self.loop:
            await asyncio.gather(self.loop, return_exceptions=True)
        await self.client.aclose()

    async def submit(self, project_id, purpose, title, request_key, args):
        if not request_key or len(request_key) > 160:
            raise ValueError("需要稳定且不超过160字符的制作请求标识")
        for job in self.store.records(project_id, "jobs"):
            if job["request_key"] == request_key:
                if job["purpose"] != purpose or job["args"] != args:
                    raise ValueError("该制作请求标识已用于另一份输入；修改后请使用新标识")
                return job
            unit_id = args.get("unit_id")
            prior_unit = job.get("unit_id") or job["args"].get("unit_id")
            if (job.get("failure_code") == "content_policy" and purpose in {"video", "videoFallback"}
                    and job["args"].get("prompt") == args.get("prompt")
                    and job["args"].get("references", []) == args.get("references", [])):
                raise ValueError("此生成内容已被服务审核拒绝，不能改参数、请求身份或Provider重复提交原内容")
            unresolved = job["status"] in self.active_states | {"unknown", "download_failed", "query_failed"}
            has_result_to_retrieve = job["status"] == "failed" and (job.get("result") or (job.get("external_id") and job.get("provider_state") not in {"failed", "cancelled", "expired"}))
            if unit_id and prior_unit == unit_id and (unresolved or has_result_to_retrieve):
                raise ValueError(f"同一制作对象已有待完成、待核对或待取回的任务 {job['id']}，请先查询或恢复下载；不能换请求标识或 Provider 重复生成")
        snapshot = None
        if purpose != "compose":
            binding = self.config.binding(purpose)
            if args.get("expected_model") and args["expected_model"] != binding.model:
                raise ValueError("模型用途已改变或与计划型号不一致，已在提交前停止；请核对当前配置")
            snapshot = {k: v for k, v in asdict(binding).items() if k != "key"}
        return self.store.put_record(project_id, "jobs", {"purpose": purpose, "title": title,
            "request_key": request_key, "args": args, "binding": snapshot, "status": "pending",
            "epoch": self.store.project(project_id)["epoch"], "basis": self.store.project(project_id)["adopted"],
            "authorization_mode": self.store.project(project_id)["mode"],
            "external_id": None, "artifact_ids": [],
            "usage": {}, "cost": None, "started": None, "finished": None})

    async def _loop(self):
        while not self.closing:
            for project in self.store.projects():
                for job in self.store.records(project["id"], "jobs"):
                    jid = job["id"]
                    if job["status"] not in self.active_states or (jid in self.tasks and not self.tasks[jid].done()):
                        continue
                    if job["status"] == "pending" and project.get("production_paused"):
                        self.store.update_record(jid, status="cancelled_local", finished=now())
                        continue
                    self.tasks[jid] = asyncio.create_task(self._run(jid))
            await asyncio.sleep(0.35)

    def binding(self, job):
        b = job["binding"]
        key = self.config.vault.get(b["connection_id"]) or ""
        connection = self.config.connection(b["connection_id"])
        if not key and not connection.get("no_key"):
            raise ValueError("此任务原连接的凭据缺失，请恢复配置后重试查询")
        return Binding(**b, key=key)

    async def _run(self, job_id):
        job = self.store.record(job_id)
        purpose = job["purpose"]
        group = "video" if purpose in {"video", "videoFallback"} else "audio" if purpose in {"voice", "music"} else purpose
        async with self.semaphores[group]:
            job = self.store.record(job_id)
            if job["status"] not in self.active_states:
                return
            if job["status"] == "pending" and self.store.project(job["project_id"]).get("production_paused"):
                self.store.update_record(job_id, status="cancelled_local", finished=now())
                return
            try:
                if job["status"] == "pending" and self.gate:
                    self.gate(job["project_id"], job["args"]["stage"], purpose, job["args"]["basis_id"])
                if purpose == "compose":
                    self.store.update_record(job_id, status="rendering", started=job["started"] or now())
                    result = await self.media.render(job)
                    artifact = self.store.create_artifact(job["project_id"], job["args"]["kind"], job["title"],
                        meta={**result, "job_id": job_id, "basis": job.get("basis", {}),
                              "parent": job.get("basis", {}).get("film")},
                        path=result["path"])
                    await self._finish(job, [artifact["id"]], {})
                    return
                if job.get("refresh_result") and job.get("external_id"):
                    result = await self._poll(Provider(self.binding(job), self.client), job)
                    saved = {k: v for k, v in asdict(result).items() if k != "data"}
                    job = self.store.update_record(job_id, result=saved, refresh_result=False)
                elif job.get("result"):
                    saved = job["result"]
                    result = MediaResult(**{k: v for k, v in saved.items() if k != "local_result"})
                else:
                    provider = Provider(self.binding(job), self.client)
                    if job.get("external_id"):
                        result = await self._poll(provider, job)
                    else:
                        if purpose in {"video", "videoFallback"}:
                            parameters = self.config.video_parameters(job["args"]["parameters"], provider.binding)
                            job = self.store.update_record(job_id, args={**job["args"], "parameters": parameters})
                        current_binding = {k: v for k, v in asdict(self.config.binding(purpose)).items() if k != "key"}
                        if current_binding != job["binding"] or (job["args"].get("expected_model")
                                and job["args"]["expected_model"] != current_binding["model"]):
                            raise ValueError("任务尚未提交，但模型用途已改变或不符合计划型号；请按当前配置重新规划，不发送旧请求")
                        args = {**job["args"]["parameters"], "prompt": job["args"]["prompt"]}
                        args["references"] = []
                        for ref in job["args"].get("references", []):
                            _, path = self.media.source(ref["artifact_id"], job["project_id"])
                            args["references"].append({"url": data_url(path), "role": ref["role"]})
                        if sum(len(r["url"]) for r in args["references"]) > 60 * 1024 * 1024:
                            raise ValueError("参考素材超出当前请求大小，请压缩或减少本次参考")
                        self.store.update_record(job_id, status="submitting", started=job["started"] or now())
                        result = await provider.submit(purpose, args)
                        if result.external_id:
                            # Persist the provider identity before polling or doing any further work.
                            job = self.store.update_record(job_id, external_id=result.external_id, status=result.state)
                            result = await self._poll(provider, job)
                if result.state != "succeeded":
                    if result.failure_code == "content_policy":
                        raise ProviderError("视频生成未通过服务内容审核；不能自动重试相同请求或切换模型绕过审核", error_type="content_policy")
                    raise ProviderError("外部任务未成功：" + result.state)
                folder = self.store.root / "media" / job_id
                folder.mkdir(parents=True, exist_ok=True)
                saved = {k: v for k, v in asdict(result).items() if k != "data"}
                if job.get("result", {}).get("local_result"):
                    saved["local_result"] = job["result"]["local_result"]
                if result.data is not None:
                    path = folder / ("output-0" + result.extension)
                    temporary = path.with_suffix(path.suffix + ".part")
                    temporary.write_bytes(result.data)
                    temporary.replace(path)
                    saved["local_result"] = path.relative_to(self.store.root).as_posix()
                self.store.update_record(job_id, status="downloading", result=saved)
                paths = []
                if saved.get("local_result"):
                    paths.append(self.store.media_path(saved["local_result"]))
                for index, url in enumerate(result.urls):
                    path = folder / (f"output-{index}" + result.extension)
                    if not path.exists():
                        await download_media(self.client, url, path)
                    paths.append(path)
                if not paths:
                    raise ProviderError("成功回执没有可保存的素材，需核对任务结果", unknown=True)
                artifact_ids = []
                subtitle_meta = {}
                if result.subtitles:
                    try:
                        subtitle_path = folder / "voice-subtitles.json"
                        if isinstance(result.subtitles, str):
                            if not subtitle_path.exists():
                                await download_media(self.client, result.subtitles, subtitle_path)
                            cues = json.loads(subtitle_path.read_text(encoding="utf-8"))
                        else:
                            cues = result.subtitles
                            subtitle_path.write_text(json.dumps(cues, ensure_ascii=False), encoding="utf-8")
                        if not isinstance(cues, list):
                            raise TypeError("字幕回执不是列表")
                        subtitle_meta = {"voice_subtitle_path": subtitle_path.relative_to(self.store.root).as_posix(),
                            "voice_cues": [{"start": float(c["time_begin"]) / 1000, "end": float(c["time_end"]) / 1000,
                                            "text": c["text"]} for c in cues], "subtitle_timing": "provider_milliseconds"}
                    except (TypeError, ValueError, KeyError, OSError, httpx.HTTPError, ProviderError):
                        subtitle_meta = {"subtitle_status": "retrieval_failed", "subtitle_note": "声音已保留，实际字幕需重新获取；未推算口型或字级对齐"}
                for path in paths:
                    relative = path.relative_to(self.store.root).as_posix()
                    existing = next((a for a in self.store.records(job["project_id"], "artifacts")
                                     if a.get("meta", {}).get("job_id") == job_id and a.get("path") == relative), None)
                    if existing:
                        artifact_ids.append(existing["id"])
                        continue
                    info = await self.media.probe(path)
                    kind = "image" if purpose == "image" else "video" if purpose in {"video", "videoFallback"} else "audio"
                    artifact = self.store.create_artifact(job["project_id"], kind, job["title"],
                        meta={"job_id": job_id, "purpose": purpose, "media": info, "references": job["args"].get("references", []),
                              "voice_id": job["args"].get("parameters", {}).get("voice_id"),
                              "subtitle_source": result.subtitles, **subtitle_meta},
                        path=relative)
                    artifact_ids.append(artifact["id"])
                await self._finish(job, artifact_ids, result.usage)
            except asyncio.CancelledError:
                if not self.closing and purpose == "compose":
                    self.store.update_record(job_id, status="cancelled_local", finished=now())
                raise
            except (ProviderError, ValueError, OSError, httpx.HTTPError) as exc:
                unknown = isinstance(exc, ProviderError) and exc.unknown
                current = self.store.record(job_id)
                state = ("download_failed" if current.get("result") else "query_failed" if current.get("external_id")
                         and current.get("provider_state") not in {"failed", "cancelled", "expired"} else "unknown" if unknown else "failed")
                if isinstance(exc, ProviderError) and exc.status_code == 410:
                    checks = self.store.setting("generation_checks", {})
                    checks[purpose] = {"status": "unavailable", "model": job["binding"]["model"],
                                       "connection_id": job["binding"]["connection_id"], "time": now(), "message": str(exc)}
                    self.store.save_setting("generation_checks", checks)
                message = str(exc) if isinstance(exc, (ProviderError, ValueError)) else "素材下载或本地处理失败，可重试获取已有结果"
                await self._publish(job, f"任务 {job_id}（{job['title']}）受阻：{message}。保留原输入和任务身份，不能重复猜测生成成功。",
                    status=state, error=message, error_type=getattr(exc, "error_type", None) or type(exc).__name__, finished=now(),
                    download_http_status=exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None)
            except Exception as exc:  # noqa: BLE001 -- retain ambiguous boundary state without exposing request data
                await self._publish(job, f"任务 {job_id} 处理异常（{type(exc).__name__}），请核对已有结果。",
                    status="unknown", error=f"任务处理异常（{type(exc).__name__}），请核对已有结果", finished=now())

    async def _poll(self, provider, job):
        while not self.closing:
            try:
                result = await provider.query(job["external_id"])
            except ProviderError as exc:
                if exc.retryable:
                    await asyncio.sleep(8)
                    continue
                raise
            if result.state != "succeeded":
                self.store.update_record(job["id"], status=result.state)
            self.store.update_record(job["id"], provider_state=result.state, failure_code=result.failure_code)
            if result.state in {"succeeded", "failed", "cancelled", "expired"}:
                return result
            if result.state not in {"queued", "running"}:
                raise ProviderError("服务返回未知任务状态，需要核对")
            await asyncio.sleep(6)
        raise asyncio.CancelledError

    async def _finish(self, job, artifact_ids, usage):
        if self.store.record(job["id"])["status"] == "succeeded":
            return
        p = self.store.project(job["project_id"])
        stale = job["epoch"] != p["epoch"] or p.get("production_paused")
        text = f"任务 {job['id']}（{job['title']}）已完成，真实产物ID：{artifact_ids}。"
        if stale:
            text += "制作期间版本或状态已变化，结果仅保留为候选，请评估复用，不得覆盖新版本或用户草稿。"
        await self._publish(job, text, status="succeeded", artifact_ids=artifact_ids, usage=usage,
                            finished=now(), candidate_only=stale, error=None)

    async def _publish(self, job, text, **changes):
        suffix = "succeeded" if changes["status"] == "succeeded" else uid()
        delivery = ("result-" + job["id"] + "-" + suffix, text, "media_task")
        self.store.update_record(job["id"], **changes, delivery=delivery)
        self.store.event(job["project_id"], "task_notice", {"text": text, "job_id": job["id"]})
        if self.notify and not self.store.project(job["project_id"]).get("production_paused"):
            try:
                await self.notify(job["project_id"], text, source=delivery[2], input_id=delivery[0])
            except Exception as exc:  # noqa: BLE001 -- never serialize SDK exceptions
                self.store.event(job["project_id"], "delivery_delayed", {"input_id": delivery[0], "error_type": type(exc).__name__})

    async def stop(self, project_id):
        for job in self.store.records(project_id, "jobs"):
            if job["status"] == "pending":
                self.store.update_record(job["id"], status="cancelled_local", finished=now())
            elif job["purpose"] == "compose" and job["id"] in self.tasks:
                self.tasks[job["id"]].cancel()
            elif job["status"] in self.active_states:
                self.store.update_record(job["id"], stop_requested=True)
        # Deliberately no H3 DELETE call: it can delete completed task records.

    async def recover(self, project_id, job_id, external_id=None):
        job = self.store.record(job_id, project_id, "jobs")
        if job["status"] in self.active_states or job["status"] == "succeeded":
            raise ValueError("任务正在处理或已经完成，不需要重复恢复")
        if external_id:
            if job["purpose"] not in {"video", "videoFallback"}:
                raise ValueError("只有异步视频任务可绑定外部任务身份")
            if job.get("external_id") and job["external_id"] != external_id:
                raise ValueError("已绑定的云端任务身份不可替换；请恢复原任务")
            result = await Provider(self.binding(job), self.client).query(external_id)
            saved = {k: v for k, v in asdict(result).items() if k != "data"} if result.state == "succeeded" else None
            self.store.update_record(job_id, external_id=external_id, status="downloading" if saved else "queued",
                                     result=saved, recovery_verified_state=result.state)
        elif job.get("external_id") or job.get("result"):
            refresh = bool(job.get("external_id") and job.get("result") and job.get("download_http_status") in {401, 403, 404, 410})
            self.store.update_record(job_id, status="downloading" if job.get("result") else "queued", refresh_result=refresh)
        else:
            raise ValueError("提交结果不明且没有外部任务身份，不能自动重复生成；请先核对服务端记录")
        return self.store.record(job_id)
