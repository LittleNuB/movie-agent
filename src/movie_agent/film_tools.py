"""Film-domain tools and version-bound co-creation gates."""

import json
from typing import Literal

from agentscope.message import TextBlock
from agentscope.tool import FunctionTool, ToolChunk

from .providers import Provider, ProviderError
from .store import Conflict

REVIEW_KINDS = {"proposal", "script", "visual_plan", "trial", "edit_plan", "film"}


class FilmTools:
    def __init__(self, store, config, runtime, jobs, media):
        self.store, self.config, self.runtime, self.jobs, self.media = store, config, runtime, jobs, media

    def public_snapshot(self, project_id):
        snapshot = self.store.snapshot(project_id)
        snapshot["models"] = self.config.public()
        # Paths are private implementation details; tool references are artifact identities.
        for item in snapshot["artifacts"]:
            item.pop("path", None)
        return snapshot

    def check_gate(self, project_id, stage, purpose, basis_id=None):
        p = self.store.project(project_id)
        if p.get("production_paused"):
            raise Conflict("影片已中止，用户明确继续前不能新增制作")
        basis = self.store.record(basis_id, project_id, "artifacts") if basis_id else None
        if stage not in {"visual", "trial", "production", "edit"}:
            raise ValueError("未知制作阶段")
        if stage == "visual" and purpose != "image":
            raise Conflict("视觉准备阶段只制作参考图片；视频和合成须先完成实际视觉审核")
        if not basis or basis.get("kind") not in {"script", "visual_plan", "shot_plan", "edit_plan"}:
            raise ValueError("制作需要具体剧本、视觉或镜头计划、修改方案作为依据")
        if basis["kind"] in {"script", "visual_plan", "edit_plan"} and p["adopted"].get(basis["kind"]) != basis_id:
            raise Conflict("直接制作依据必须是已采用的那个具体版本；请先记录审核或托管采用")
        if basis["kind"] == "shot_plan" and basis.get("meta", {}).get("basis", {}).get("script") != p["adopted"].get("script"):
            raise Conflict("镜头计划的剧本依据已过时，请基于当前采用剧本更新计划")
        for kind, aid in basis.get("meta", {}).get("basis", {}).items():
            if kind in {"script", "visual_plan", "trial"} and p["adopted"].get(kind) != aid:
                raise Conflict("制作依据已经过时，请先核对新版本")
        if p["mode"] == "audio" and purpose in {"voice", "music", "sfx"}:
            if "script" not in p["adopted"]:
                raise Conflict("故事与剧本仍需共创审核后再进入声音制作")
            return
        required = {"visual": ["script"], "trial": ["script", "visual_plan"],
                    "production": ["script", "visual_plan", "trial"], "edit": ["edit_plan"]}.get(stage)
        if required is None:
            raise ValueError("请明确这是 visual、trial、production 还是 edit 制作阶段")
        missing = [kind for kind in required if kind not in p["adopted"]]
        if missing:
            raise Conflict("制作前需要记录采用的实际产物：" + "、".join(missing) + "。托管模式调用 request_review 会直接记录托管决定，无需等待用户。")
        for adopted_kind in required:
            adopted = self.store.record(p["adopted"][adopted_kind], project_id, "artifacts")
            for dependency, aid in adopted.get("meta", {}).get("basis", {}).items():
                if dependency in {"proposal", "script", "visual_plan"} and p["adopted"].get(dependency) != aid:
                    raise Conflict("当前采用的下游产物仍依据旧版本，需核对并重新审核后制作")
        if stage == "edit" and basis_id != p["adopted"].get("edit_plan"):
            raise Conflict("请使用已批准的具体修改方案作为制作依据")
        if stage == "edit" and basis.get("meta", {}).get("scope") == "audio" and purpose in {"image", "video", "videoFallback"}:
            raise Conflict("只涉及声音的方案不能授权补拍画面；请说明画面影响并按当前模式确认")

    def request_review(self, project_id, artifact_id, question):
        artifact = self.store.record(artifact_id, project_id, "artifacts")
        if artifact["kind"] not in REVIEW_KINDS:
            raise ValueError("此产物类型不需要创作审核")
        if artifact["kind"] == "visual_plan":
            assets = artifact.get("meta", {}).get("asset_ids", [])
            if not assets or any(not self.store.record(aid, project_id, "artifacts").get("path") for aid in assets):
                raise ValueError("视觉审核需要实际生成的参考图，请先在 visual_plan.data.asset_ids 中加入可查看的图片身份")
        if artifact["kind"] in {"trial", "film"} and not artifact.get("path"):
            raise ValueError("试拍和影片审核需要真实媒体文件")
        p = self.store.project(project_id)
        if artifact.get("meta", {}).get("candidate_only"):
            raise Conflict("迟到候选不能直接覆盖采用决定，请按当前版本重新核对并形成方案")
        if ("parent" in artifact.get("meta", {}) and p["adopted"].get(artifact["kind"]) != artifact_id
                and artifact["meta"]["parent"] != p["adopted"].get(artifact["kind"])):
            raise Conflict("此产物所修改的原版本已变化，请保留候选并基于当前决定核对")
        for kind, aid in artifact.get("meta", {}).get("basis", {}).items():
            if kind in {"proposal", "script", "visual_plan", "trial", "film"} and p["adopted"].get(kind) != aid:
                raise Conflict("此候选产物依据旧版本制作，不能自动改变新采用状态；请先核对并基于当前决定形成方案。历史恢复须由用户明确采用。")
        for review in self.store.records(project_id, "reviews"):
            if review["artifact_id"] == artifact_id and (review["status"] == "pending"
                    or review["status"] == "approved" and p["adopted"].get(artifact["kind"]) == artifact_id):
                return review
        auto = p["mode"] == "auto" or (p["mode"] == "audio" and artifact["kind"] == "edit_plan"
                                       and artifact.get("meta", {}).get("scope") == "audio")
        review = self.store.put_record(project_id, "reviews", {
            "artifact_id": artifact_id, "kind": artifact["kind"], "question": question,
            "base": p["adopted"].get(artifact["kind"]), "status": "pending",
            "dependencies": {k: v for k, v in p["adopted"].items() if k in {
                "script": ["proposal"], "visual_plan": ["script"], "trial": ["script", "visual_plan"],
                "edit_plan": ["script", "film"], "film": ["script", "visual_plan", "trial"]
            }.get(artifact["kind"], [])},
            "authority": "delegated_mode" if auto else "awaiting_user", "mode": p["mode"]})
        if auto:
            review = self.store.decide_review(project_id, review["id"], True, authority="delegated_mode")
        else:
            self.store.update_project(project_id, status="waiting_review")
        return review

    def decide_review(self, project_id, review_id, approve, feedback=""):
        return self.store.decide_review(project_id, review_id, approve, feedback)

    def review_from_message(self, project_id, review_id, user_message_id, approve, feedback):
        message = self.store.record(user_message_id, project_id, "messages")
        review = self.store.record(review_id, project_id, "reviews")
        if message.get("role") != "user" or message["created"] < review["created"]:
            raise Conflict("请引用此审核提出之后、用户针对该内容的实际回复")
        return self.store.decide_review(project_id, review_id, approve, feedback,
                                        authority="user_message", evidence_message_id=user_message_id)

    def for_agent(self, project_id, role, starting_basis=None):
        observed_basis = dict(starting_basis if starting_basis is not None else self.store.project(project_id)["adopted"])

        def current_scope():
            current = self.store.project(project_id)["adopted"]
            if role != "director" and current != observed_basis:
                raise Conflict("专业任务依据已改变，请将已有结果作为候选交还导演，不再按旧任务制作")

        def output(value):
            return ToolChunk(content=[TextBlock(text=json.dumps(value, ensure_ascii=False))], state="success")

        async def read_project():
            """Read current film, artifact IDs, approvals, tasks and available model assignments."""
            data = self.public_snapshot(project_id)
            if role == "director":
                observed_basis.clear()
                observed_basis.update(data["project"]["adopted"])
            # Messages already live in the conversation; avoid duplicating the whole conversation in every tool result.
            data["messages"] = data["messages"][-8:]
            data["runs"] = [{k: v for k, v in r.items() if k != "result"} for r in data["runs"][-8:]]
            for item in data["artifacts"]:
                item["text"] = item["text"][:450]
                item["meta"] = {k: v for k, v in item["meta"].items()
                                if k in {"basis", "asset_ids", "parent", "media", "job_id", "manual", "evidence"}}
            for item in data["jobs"]:
                item.pop("result", None)
                item["args"] = {k: v for k, v in item["args"].items() if k in {"stage", "basis_id", "references", "parameters"}}
            return output(data)

        async def read_artifact(artifact_id: str):
            """Read the complete immutable document, shot plan, or film edit metadata by its identity.
            read_project contains summaries only. Read full scripts and plans before changing or producing them.
            """
            item = self.store.record(artifact_id, project_id, "artifacts")
            item.pop("path", None)
            return output(item)

        async def publish_document(kind: Literal["proposal", "script", "visual_plan", "shot_plan", "edit_plan", "continuity_check"],
                                   title: str, text: str, data: dict | None = None):
            """Save an immutable actual document. data carries structured characters/scenes/shots/asset_ids/scope.
            This does not approve the document or change the user's draft. Request review separately.
            """
            meta = data or {}
            for ref in meta.get("asset_ids", []):
                self.store.record(ref, project_id)
            p = self.store.project(project_id)
            artifact = self.store.create_artifact(project_id, kind, title, text,
                {**meta, "basis": {k: v for k, v in observed_basis.items() if k in {
                    "script": ["proposal"], "visual_plan": ["script"], "shot_plan": ["script", "visual_plan"],
                    "edit_plan": ["script", "film"]}.get(kind, [])},
                 "parent": observed_basis.get(kind), "author": role,
                 "candidate_only": p["adopted"] != observed_basis})
            if kind == "proposal" and p["title"] in {"新影片", "未命名影片"}:
                self.store.update_project(project_id, title=title)
            return output(artifact)

        async def request_review(artifact_id: str, question: str):
            """Request review of a concrete proposal/script/visual_plan/trial/edit_plan.
            If pending, end this turn and wait. Delegated scopes return recorded approval.
            """
            review = self.request_review(project_id, artifact_id, question)
            if review["status"] == "approved":
                observed_basis.clear()
                observed_basis.update(self.store.project(project_id)["adopted"])
            return output(review)

        async def record_user_review(review_id: str, user_message_id: str, approve: bool, feedback: str):
            """Record a user's natural-language decision on a specific pending review.
            Cite the actual user message after that review; only explicit, unambiguous approval or rejection counts.
            A question, saving a draft, silence, or a specialist conclusion is not approval.
            If multiple reviews make the referent ambiguous, clarify before calling.
            """
            review = self.review_from_message(project_id, review_id, user_message_id, approve, feedback)
            if review["status"] == "approved":
                observed_basis.clear()
                observed_basis.update(self.store.project(project_id)["adopted"])
            return output(review)

        async def generate_media(purpose: Literal["image", "video", "videoFallback", "voice", "music"],
                                 title: str, prompt: str, request_key: str, unit_id: str, expected_model: str,
                                 stage: Literal["visual", "trial", "production", "edit"],
                                 basis_id: str, parameters: dict | None = None, references: list[dict] | None = None):
            """Submit a background media task; returns immediately. Do not duplicate pending requests.
            request_key uniquely identifies this shot/asset attempt (e.g. shot-3-v1); reuse returns its task.
            unit_id is the stable shot/character/voice-line identity in the plan (e.g. SH3); keep it across attempts and Providers.
            parameters: duration, resolution, size; voice_id, speed, emotion for voice.
            Current generation specification: H3 uses 768P; Ark uses 720p. Read current model assignments.
            expected_model must be the exact model ID assigned to purpose, so an intended fallback cannot silently use the primary.
            Never use seconds as a parameter key. Already submitted cloud tasks keep their original parameters.
            references: [{artifact_id,role}], where role is first_frame/last_frame/reference_image/reference_audio/reference_video.
            basis_id is the concrete plan/script ID; edit stage requires the approved edit_plan ID.
            """
            current_scope()
            self.check_gate(project_id, stage, purpose, basis_id)
            binding = self.config.binding(purpose)
            if binding.model != expected_model:
                raise ValueError(f"所选用途实际模型为 {binding.model}，与计划型号 {expected_model} 不一致；请读取当前用途分配后明确选择")
            if purpose in {"video", "videoFallback"}:
                parameters = self.config.video_parameters(parameters or {}, binding)
            Provider(binding, self.jobs.client).validate(purpose, parameters or {}, references or [])
            if not unit_id.strip() or len(unit_id) > 160:
                raise ValueError("需要稳定的镜头或素材对象身份")
            for ref in references or []:
                artifact = self.store.record(ref["artifact_id"], project_id)
                if not artifact.get("path"):
                    raise ValueError("参考资产必须已有真实媒体文件")
                expected = "audio" if ref["role"] == "reference_audio" else "video" if ref["role"] == "reference_video" else "image"
                if artifact["kind"] != expected:
                    raise ValueError("参考角色与素材类型不匹配；视频需先 extract_frame 再作为图片引用")
            job = await self.jobs.submit(project_id, purpose, title, request_key,
                {"prompt": prompt, "parameters": parameters or {}, "references": references or [],
                 "stage": stage, "basis_id": basis_id, "unit_id": unit_id, "expected_model": expected_model})
            return output(job)

        async def compose(title: str, kind: Literal["trial", "film"], request_key: str,
                          stage: Literal["trial", "production", "edit"], basis_id: str,
                          clips: list[dict], tracks: list[dict] | None = None,
                          subtitles: list[dict] | None = None, picture_master_id: str | None = None):
            """Render actual media in the background. clips: [{artifact_id,start,duration,audio_gain,speed,fade_in,fade_out}].
            clip start is source time; duration is output seconds; speed defaults to 1, supports 0.25–4 with pitch-preserving native audio.
            tracks: [{artifact_id,start,gain,loop,source_start,duration,fade_in,fade_out}]; start is output time; source_start/duration trim its source audio.
            Tracks may reference actual mixed video sound; never pretend it contains separate dialogue or SFX stems. subtitles: [{start,end,text}].
            For music-only edits reuse picture_master_id from the prior film metadata and preserve its clips.
            Only completed artifacts may be referenced. Total film duration must be 90–120 seconds.
            """
            current_scope()
            self.check_gate(project_id, stage, "compose", basis_id)
            basis = self.store.record(basis_id, project_id, "artifacts")
            if stage == "edit" and basis.get("meta", {}).get("scope") == "audio":
                prior_id = self.store.project(project_id)["adopted"].get("film")
                if not prior_id:
                    raise ValueError("独立声音修改需要已有影片")
                prior = self.store.record(prior_id, project_id, "artifacts")
                if picture_master_id != prior.get("meta", {}).get("picture_master_id"):
                    raise Conflict("声音修改需要明确复用采用影片的画面母版")
            for entry in clips + (tracks or []):
                artifact = self.store.record(entry["artifact_id"], project_id)
                if not artifact.get("path"):
                    raise ValueError("合成素材尚未生成")
            if picture_master_id:
                master = self.store.record(picture_master_id, project_id)
                if master["kind"] != "picture_master":
                    raise ValueError("画面母版身份不正确")
            job = await self.jobs.submit(project_id, "compose", title, request_key,
                {"kind": kind, "stage": stage, "basis_id": basis_id, "clips": clips, "tracks": tracks or [],
                 "subtitles": subtitles or [], "picture_master_id": picture_master_id})
            return output(job)

        async def inspect_media(artifact_ids: list[str], question: str):
            """Inspect actual image/video frames using the assigned vision model and project context.
            Result names source IDs and frame times. This does not listen to audio or approve quality.
            """
            return output(await self.media.inspect(project_id, artifact_ids, question, self.runtime))

        async def export_film_version(source_film_id: str, title: str, request_key: str, basis_id: str):
            """Derive current-format output while preserving the source film's exact edit, tracks and subtitles.
            Use for export-only changes instead of reconstructing clips/tracks from memory.
            Requires a concrete adopted edit_plan. Reuses the source picture master; makes no generation calls.
            """
            current_scope()
            self.check_gate(project_id, "edit", "compose", basis_id)
            source = self.store.record(source_film_id, project_id, "artifacts")
            if source["kind"] not in {"film", "trial"} or not source.get("path") or not source["meta"].get("edit"):
                raise ValueError("导出需要已有真实影片和完整剪辑记录")
            args = {**source["meta"]["edit"], "kind": source["kind"], "stage": "edit", "basis_id": basis_id,
                    "picture_master_id": source["meta"].get("picture_master_id"), "source_film_id": source_film_id}
            return output(await self.jobs.submit(project_id, "compose", title, request_key, args))

        async def extract_frame(artifact_id: str, time: float, title: str):
            """Save an actual frame from a completed project video as a reusable image reference."""
            return output(await self.media.extract_frame(project_id, artifact_id, time, title))

        async def recover_task(job_id: str):
            """Query a known cloud task or fetch its saved result again, without submitting a new generation.
            Unknown submissions without an external identity require provider-side evidence; this cannot guess an ID.
            """
            return output(await self.jobs.recover(project_id, job_id))

        async def voice_catalog():
            """Read available system voice IDs for the assigned voice connection. No audio generation."""
            provider = Provider(self.config.binding("voice"), self.jobs.client)
            result = await provider.discover()
            result["voices"] = result.get("voices", [])[:60]
            return output(result)

        async def delegate(specialist: Literal["visual", "post", "check"], task: str):
            """Dispatch specialist work in the background and immediately return its run_id.
            Include relevant artifact IDs and constraints. Findings arrive later in the director inbox.
            Specialist findings are not user approval; generation still obeys current project gates.
            """
            return output(await self.runtime.delegate(project_id, specialist, task, basis=observed_basis))

        async def resume_production(user_message_id: str, reason: str):
            """Resume only after a user explicitly asks to continue. Cite the actual user message ID.
            A discussion question after stopping is not permission to resume production.
            """
            message = self.store.record(user_message_id, project_id)
            if message.get("role") != "user" or message["created"] <= self.store.project(project_id).get("stopped_at", ""):
                raise ValueError("继续制作需要引用用户的实际消息")
            self.store.put_record(project_id, "authorizations", {"action": "resume", "message_id": user_message_id,
                                                                 "reason": reason})
            return output(self.store.update_project(project_id, production_paused=False, status="idle"))

        functions = [read_project, read_artifact, publish_document, generate_media, compose, export_film_version, inspect_media, extract_frame, recover_task, voice_catalog]
        if role == "director":
            functions += [request_review, record_user_review, delegate, resume_production]
        result = []
        for func in functions:
            async def guarded(_function=func, **kwargs):
                try:
                    return await _function(**kwargs)
                except (ValueError, KeyError, ProviderError) as exc:
                    return ToolChunk(content=[TextBlock(text=str(exc))], state="error")
            tool = FunctionTool(func, is_concurrency_safe=func is read_project, is_read_only=func is read_project)
            # The public schema comes from the typed function; the wrapper keeps recoverable domain errors in-band.
            result.append(FunctionTool(guarded, name=tool.name, description=tool.description,
                input_schema=tool.input_schema, is_concurrency_safe=tool.is_concurrency_safe,
                is_read_only=tool.is_read_only))
        return result
