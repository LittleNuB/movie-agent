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
        if not basis or basis.get("kind") not in {"script", "visual_plan", "shot_plan", "edit_plan"}:
            raise ValueError("制作需要具体剧本、视觉或镜头计划、修改方案作为依据")
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
        for review in self.store.records(project_id, "reviews"):
            if review["artifact_id"] == artifact_id and review["status"] in {"pending", "approved"}:
                return review
        p = self.store.project(project_id)
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

    def for_agent(self, project_id, role):
        def output(value):
            return ToolChunk(content=[TextBlock(text=json.dumps(value, ensure_ascii=False))], state="success")

        async def read_project():
            """Read current film, artifact IDs, approvals, tasks and available model assignments."""
            data = self.public_snapshot(project_id)
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
                {**meta, "basis": {k: v for k, v in p["adopted"].items() if k in {
                    "script": ["proposal"], "visual_plan": ["script"], "shot_plan": ["script", "visual_plan"],
                    "edit_plan": ["script", "film"]}.get(kind, [])},
                 "parent": p["adopted"].get(kind), "author": role})
            if kind == "proposal" and p["title"] in {"新影片", "未命名影片"}:
                self.store.update_project(project_id, title=title)
            return output(artifact)

        async def request_review(artifact_id: str, question: str):
            """Request review of a concrete proposal/script/visual_plan/trial/edit_plan.
            If pending, end this turn and wait. Delegated scopes return recorded approval.
            """
            return output(self.request_review(project_id, artifact_id, question))

        async def generate_media(purpose: Literal["image", "video", "videoFallback", "voice", "music"],
                                 title: str, prompt: str, request_key: str, unit_id: str,
                                 stage: Literal["visual", "trial", "production", "edit"],
                                 basis_id: str, parameters: dict | None = None, references: list[dict] | None = None):
            """Submit a background media task; returns immediately. Do not duplicate pending requests.
            request_key uniquely identifies this shot/asset attempt (e.g. shot-3-v1); reuse returns its task.
            unit_id is the stable shot/character/voice-line identity in the plan (e.g. SH3); keep it across attempts and Providers.
            parameters: duration, resolution, size; voice_id, speed, emotion for voice.
            H3 resolution is 2K or 768P; Ark video is 720p or 1080p. Never use seconds as a parameter key.
            references: [{artifact_id,role}], where role is first_frame/last_frame/reference_image/reference_audio/reference_video.
            basis_id is the concrete plan/script ID; edit stage requires the approved edit_plan ID.
            """
            self.check_gate(project_id, stage, purpose, basis_id)
            binding = self.config.binding(purpose)
            Provider(binding, self.jobs.client).validate(purpose, parameters or {}, references or [])
            if not unit_id.strip() or len(unit_id) > 160:
                raise ValueError("需要稳定的镜头或素材对象身份")
            for ref in references or []:
                artifact = self.store.record(ref["artifact_id"], project_id)
                if not artifact.get("path"):
                    raise ValueError("参考资产必须已有真实媒体文件")
            job = await self.jobs.submit(project_id, purpose, title, request_key,
                {"prompt": prompt, "parameters": parameters or {}, "references": references or [],
                 "stage": stage, "basis_id": basis_id, "unit_id": unit_id})
            return output(job)

        async def compose(title: str, kind: Literal["trial", "film"], request_key: str,
                          stage: Literal["trial", "production", "edit"], basis_id: str,
                          clips: list[dict], tracks: list[dict] | None = None,
                          subtitles: list[dict] | None = None, picture_master_id: str | None = None):
            """Render actual media in the background. clips: [{artifact_id,start,duration,audio_gain}].
            tracks: [{artifact_id,start,gain,loop}], start is output time; subtitles: [{start,end,text}].
            For music-only edits reuse picture_master_id from the prior film metadata and preserve its clips.
            Only completed artifacts may be referenced. Total film duration must be 90–120 seconds.
            """
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
            return output(await self.runtime.delegate(project_id, specialist, task))

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

        functions = [read_project, read_artifact, publish_document, generate_media, compose, inspect_media, voice_catalog]
        if role == "director":
            functions += [request_review, delegate, resume_production]
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
