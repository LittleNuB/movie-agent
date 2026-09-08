"""Loopback-only REST/SSE application. Only explicit API actions mutate film state."""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import Binding, Configuration, ConnectionInput
from .film_tools import FilmTools
from .jobs import Jobs
from .media import Media
from .providers import Provider, ProviderError
from .runtime import Runtime
from .store import Conflict, Store, uid


class NewProject(BaseModel):
    title: str = Field(default="新影片", max_length=200)
    mode: Literal["co", "auto", "audio"] = "co"


class ProjectTitle(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class MessageInput(BaseModel):
    text: str = Field(max_length=60000)
    client_id: str = Field(default_factory=uid, pattern=r"^[A-Za-z0-9_-]{1,100}$")
    annotation_ids: list[str] = Field(default_factory=list)


class DraftInput(BaseModel):
    text: str = Field(max_length=100000)
    expected_revision: int = Field(ge=0)
    source_artifact_id: str | None = None


class RevisionInput(BaseModel):
    expected_revision: int = Field(ge=0)


class ReviewInput(BaseModel):
    approve: bool
    feedback: str = Field(default="", max_length=10000)


class AnnotationInput(BaseModel):
    artifact_id: str
    time: float = Field(ge=0, le=7200)
    text: str = Field(min_length=1, max_length=10000)


class AdoptInput(BaseModel):
    artifact_id: str
    expected: str | None = None


class ModeInput(BaseModel):
    mode: Literal["co", "auto", "audio"]


class RecoveryInput(BaseModel):
    external_id: str | None = None


def create_app(data_root=None, *, vault=None, enable_runtime=True):
    repo = Path(__file__).resolve().parents[2]
    store = Store(Path(data_root or os.environ.get("MOVIE_AGENT_DATA", repo / "local-data")))
    config = Configuration(store, vault)
    runtime = Runtime(store, config)
    media = Media(store)
    jobs = Jobs(store, config, media)
    film = FilmTools(store, config, runtime, jobs, media)
    runtime.tool_factory = film.for_agent
    jobs.notify = runtime.notify
    jobs.gate = film.check_gate

    @asynccontextmanager
    async def lifespan(app):
        if enable_runtime:
            await runtime.start()
            await jobs.start()
        yield
        await jobs.close()
        if enable_runtime:
            await runtime.close()

    app = FastAPI(title="Movie Agent", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store, app.state.config = store, config
    app.state.runtime, app.state.jobs, app.state.film = runtime, jobs, film

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        host = request.url.hostname
        if host not in {"127.0.0.1", "localhost"}:
            return JSONResponse({"error": "只接受本机访问"}, 403)
        origin = request.headers.get("origin")
        if origin and (urlsplit(origin).netloc != request.headers.get("host") or urlsplit(origin).scheme != "http"):
            return JSONResponse({"error": "请求来源不匹配"}, 403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "不接受跨站请求"}, 403)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"error": "写入请求必须使用 JSON"}, 415)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # FastAPI's default response includes input values; API Key fields must never be echoed.
        return JSONResponse({"error": "输入格式不正确", "fields": [list(e["loc"]) for e in exc.errors()]}, 422)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"error": str(exc)}, 409)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"error": str(exc)}, 400)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"error": "内容不存在或不属于当前影片"}, 404)

    @app.exception_handler(ProviderError)
    async def provider_error(request, exc):
        return JSONResponse({"error": str(exc), "unknown": exc.unknown}, 502)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "runtime": "agentscope-2.0.7.post1", "ffmpeg": bool(media.ffmpeg), "simulated": False}

    @app.get("/api/config")
    async def settings():
        return config.public()

    @app.put("/api/connections")
    async def save_connection(body: ConnectionInput):
        return config.save(body)

    @app.delete("/api/connections/{connection_id}")
    async def delete_connection(connection_id: str):
        return config.delete(connection_id)

    @app.put("/api/assignments")
    async def assignments(body: dict[str, str]):
        return config.assign(body)

    @app.post("/api/connections/{connection_id}/check")
    @app.post("/api/connections/{connection_id}/models")
    async def check_connection(connection_id: str):
        c = config.connection(connection_id)
        key = config.vault.get(connection_id) or ""
        if not key and not c["no_key"]:
            raise ValueError("请先保存此连接的 API Key")
        binding = Binding(c["id"], c["protocol"], c["base_url"], "", {}, key)
        return await Provider(binding, jobs.client).discover()

    @app.get("/api/projects")
    async def list_projects():
        return store.projects()

    @app.post("/api/projects")
    async def new_project(body: NewProject):
        return store.create_project(body.title, body.mode)

    @app.get("/api/projects/{pid}")
    async def project(pid: str):
        snapshot = film.public_snapshot(pid)
        snapshot["activities"] = store.records(pid, "activities")[-250:]
        snapshot["inputs"] = [{k: item.get(k) for k in ("id", "status", "source", "created", "run_id")}
                              for item in store.records(pid, "inputs")]
        return snapshot

    @app.put("/api/projects/{pid}/title")
    async def rename_project(pid: str, body: ProjectTitle):
        if not body.title.strip():
            raise ValueError("请填写影片名称")
        return store.update_project(pid, title=body.title.strip())

    @app.post("/api/projects/{pid}/messages")
    async def message(pid: str, body: MessageInput):
        msg = store.accept_message(pid, body.client_id, body.text, body.annotation_ids)
        entry = store.record("input-" + body.client_id, pid, "inputs")
        await runtime.notify(pid, entry["text"], source="user", input_id=entry["id"])
        return msg

    @app.put("/api/projects/{pid}/draft")
    async def save_draft(pid: str, body: DraftInput):
        return store.save_draft(pid, body.text, body.expected_revision, body.source_artifact_id)

    @app.post("/api/projects/{pid}/draft/submit")
    async def submit_draft(pid: str, body: RevisionInput):
        artifact = store.submit_draft(pid, body.expected_revision)
        await runtime.notify(pid, f"用户明确提交了手改剧本 {artifact['id']}。请读取快照，先理解并提出修改意见和方案，按当前授权确认后再执行。",
                             source="user_edit", input_id="draft-" + artifact["id"])
        return artifact

    @app.post("/api/projects/{pid}/reviews/{review_id}")
    async def review(pid: str, review_id: str, body: ReviewInput):
        result = film.decide_review(pid, review_id, body.approve, body.feedback)
        await runtime.notify(pid, f"用户{'批准' if body.approve else '未批准'}了 {result['kind']} 产物 {result['artifact_id']}。反馈：{body.feedback}",
                             source="user_review", input_id="review-" + review_id)
        return result

    @app.put("/api/projects/{pid}/mode")
    async def mode(pid: str, body: ModeInput):
        delivery = ("mode-" + uid(), f"用户将当前授权模式明确改为 {body.mode}。按新范围处理后续动作，保留已有作品和批准。", "user_mode")
        p = store.update_project(pid, mode=body.mode, delivery=delivery)
        await runtime.notify(pid, delivery[1], source=delivery[2], input_id=delivery[0])
        return p

    @app.post("/api/projects/{pid}/stop")
    async def stop(pid: str):
        await runtime.stop(pid)
        await jobs.stop(pid)
        return {"project": store.project(pid), "message": "本地调度已停止。已提交的云端任务仍可能运行，其结果会保留为候选。"}

    @app.post("/api/projects/{pid}/resume")
    async def resume(pid: str):
        delivery = ("resume-" + uid(), "用户点击继续制作，请先查看保留的任务和候选，再继续未完成工作。", "user_resume")
        store.update_project(pid, production_paused=False, status="idle", delivery=delivery)
        await runtime.notify(pid, delivery[1], source=delivery[2], input_id=delivery[0])
        return store.project(pid)

    @app.post("/api/projects/{pid}/annotations")
    async def annotation(pid: str, body: AnnotationInput):
        artifact = store.record(body.artifact_id, pid)
        if artifact.get("kind") not in {"film", "trial", "video"}:
            raise ValueError("只能对真实视频或影片版本添加时间点标注")
        duration = artifact.get("meta", {}).get("media", {}).get("duration", 0)
        if body.time > duration + 0.1:
            raise ValueError("标注时间超出当前影片版本")
        return store.put_record(pid, "annotations", {**body.model_dump(), "submitted_message_id": None})

    @app.put("/api/projects/{pid}/annotations/{aid}")
    async def edit_annotation(pid: str, aid: str, body: AnnotationInput):
        item = store.record(aid, pid, "annotations")
        if item.get("submitted_message_id"):
            raise Conflict("已发送的标注保留原意见，请新增反馈")
        if item["artifact_id"] != body.artifact_id:
            raise ValueError("不能改变标注所绑定的影片版本")
        artifact = store.record(body.artifact_id, pid, "artifacts")
        if body.time > artifact.get("meta", {}).get("media", {}).get("duration", 0) + 0.1:
            raise ValueError("标注时间超出当前影片版本")
        return store.update_record(aid, text=body.text, time=body.time)

    @app.delete("/api/projects/{pid}/annotations/{aid}")
    async def remove_annotation(pid: str, aid: str):
        item = store.record(aid, pid, "annotations")
        if item.get("submitted_message_id"):
            raise Conflict("已发送标注保留在历史中")
        return store.update_record(aid, removed=True)

    @app.post("/api/projects/{pid}/adopt")
    async def adopt(pid: str, body: AdoptInput):
        artifact = store.record(body.artifact_id, pid, "artifacts")
        if artifact["kind"] not in {"film", "trial"}:
            raise ValueError("历史采用用于作品版本；剧本和视觉决定请通过审核提交")
        delivery = ("adopt-" + uid(), f"用户明确采用历史版本 {body.artifact_id} 作为继续创作的依据。当前手改草稿须保留，先讨论下一步。", "user_adopt")
        p = store.adopt(pid, body.artifact_id, body.expected, restore_basis=True, delivery=delivery)
        await runtime.notify(pid, delivery[1], source=delivery[2], input_id=delivery[0])
        return p

    @app.post("/api/projects/{pid}/jobs/{jid}/recover")
    async def recover(pid: str, jid: str, body: RecoveryInput):
        return await jobs.recover(pid, jid, body.external_id)

    @app.get("/api/events")
    async def events(request: Request, after: int = 0):
        try:
            cursor = max(after, int(request.headers.get("last-event-id", "0")))
        except ValueError:
            cursor = after
        async def stream():
            nonlocal cursor
            while not await request.is_disconnected():
                for event in store.events(cursor):
                    cursor = event["seq"]
                    # Public UI receives identifiers; it reloads authorized project snapshots.
                    data = {"project_id": event["project_id"], "kind": event["kind"],
                            "body": event["body"] if event["kind"] in {"text_delta", "activity", "task_notice"} else {}}
                    yield f"id: {cursor}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                yield ": heartbeat\n\n"
                await asyncio.sleep(0.5)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @app.get("/api/media/{artifact_id}")
    async def media_file(artifact_id: str):
        artifact = store.record(artifact_id)
        _, path = media.source(artifact_id, artifact["project_id"])
        codec = next((s.get("codec_name") for s in artifact.get("meta", {}).get("media", {}).get("streams", [])
                      if s.get("codec_type") == "video"), None)
        content_type = {"mjpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(codec) if artifact.get("kind") == "image" else None
        return FileResponse(path, filename=None, media_type=content_type)

    @app.get("/api/artifacts/{artifact_id}/download")
    async def download(artifact_id: str):
        artifact = store.record(artifact_id)
        if artifact.get("path"):
            _, path = media.source(artifact_id, artifact["project_id"])
            return FileResponse(path, filename=path.name)
        return JSONResponse({"title": artifact["title"], "text": artifact["text"], "meta": artifact["meta"]})

    @app.get("/api/artifacts/{artifact_id}/subtitles")
    async def subtitles(artifact_id: str, format: Literal["vtt", "srt"] = "vtt"):
        artifact = store.record(artifact_id, category="artifacts")
        relative = artifact.get("meta", {}).get("vtt_path" if format == "vtt" else "subtitle_path")
        if not relative:
            raise KeyError("此影片没有字幕")
        return FileResponse(store.media_path(relative), media_type="text/vtt" if format == "vtt" else "application/x-subrip",
                            filename=None if format == "vtt" else "subtitles.srt")

    @app.get("/")
    async def index():
        return FileResponse(repo / "web/index.html")

    @app.get("/{filename}")
    async def static(filename: str):
        if filename not in {"app.js", "settings.js", "workspace.js", "panels.js", "styles.css", "workspace.css"}:
            return JSONResponse({"error": "Not found"}, 404)
        return FileResponse(repo / "web" / filename)

    return app
