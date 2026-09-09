"""Explicit media protocols, with no automatic retries of ambiguous submissions."""

import asyncio
import base64
import ipaddress
import mimetypes
import socket
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import getproxies

import httpx

from .config import Binding


class ProviderError(Exception):
    def __init__(self, message, *, unknown=False, retryable=False, status_code=None, error_type=None):
        super().__init__(message)
        self.unknown = unknown
        self.retryable = retryable
        self.status_code = status_code
        self.error_type = error_type


@dataclass
class MediaResult:
    state: str
    external_id: str | None = None
    urls: list[str] = field(default_factory=list)
    data: bytes | None = field(default=None, repr=False)
    extension: str = ".mp4"
    usage: dict = field(default_factory=dict)
    subtitles: list | str | None = None
    failure_code: str | None = None


def data_url(path: Path):
    header = path.read_bytes()[:16]
    mime = ("image/jpeg" if header.startswith(b"\xff\xd8\xff") else "image/png" if header.startswith(b"\x89PNG")
            else mimetypes.guess_type(str(path))[0] or "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


class Provider:
    def __init__(self, binding: Binding, client: httpx.AsyncClient):
        self.binding = binding
        self.client = client

    def validate(self, purpose, parameters, references=()):
        allowed = {"image": {"size"}, "video": {"duration", "resolution"},
                   "videoFallback": {"duration", "resolution"}, "voice": {"voice_id", "speed", "emotion"}, "music": set()}
        unknown = set(parameters) - allowed.get(purpose, set())
        if unknown:
            raise ProviderError("此生成用途不支持参数：" + "、".join(sorted(unknown)) + "。视频时长使用 duration（秒）。")
        if purpose == "voice" and self.binding.protocol == "minimax_audio":
            speed = parameters.get("speed", 1)
            if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not 0.5 <= speed <= 2:
                raise ProviderError("配音 speed 必须在0.5–2之间")
            emotions = {"happy", "sad", "angry", "fearful", "disgusted", "surprised", "calm"}
            if self.binding.model in {"speech-2.6-hd", "speech-2.6-turbo"}:
                emotions |= {"fluent", "whisper"}
            emotion = parameters.get("emotion")
            if emotion is not None and (not isinstance(emotion, str) or emotion not in emotions):
                raise ProviderError("配音 emotion 需要接口支持的枚举：" + ", ".join(sorted(emotions))
                                    + "；复杂情绪用创作说明记录，或省略 emotion 让语音模型判断。请求尚未发送。")
        if purpose in {"video", "videoFallback"}:
            duration = parameters.get("duration", 10)
            is_max = self.binding.model == "MiniMax-H3-Max"
            minimum = 4 if self.binding.protocol == "minimax_video" and not is_max else 5
            if isinstance(duration, bool) or not isinstance(duration, (int, float)) or int(duration) != duration or not minimum <= duration <= 15:
                raise ProviderError(f"所选视频模型时长必须为{minimum}–15之间的整数秒")
            is_seedance_fast = self.binding.model.startswith("doubao-seedance-2-0-fast")
            resolutions = (({"480P", "768P"} if is_max else {"2K", "768P"}) if self.binding.protocol == "minimax_video"
                           else {"480p", "720p"} if is_seedance_fast else {"720p", "1080p"})
            if parameters.get("resolution", next(iter(resolutions))) not in resolutions:
                raise ProviderError("所选生成接口支持的分辨率为 " + "、".join(sorted(resolutions)) + "；生成规格与后期导出规格分别记录。")
            roles = {r["role"] for r in references}
            if roles - {"first_frame", "last_frame", "reference_image", "reference_audio", "reference_video"}:
                raise ProviderError("未知参考素材用途")
            if self.binding.protocol == "ark" and "last_frame" in roles and "first_frame" not in roles:
                raise ProviderError("尾帧路径需要同时提供首帧")
            if is_max and roles & {"reference_image", "reference_audio", "reference_video"}:
                raise ProviderError("此极速模型不支持多模态参考，请选择首尾帧路径或支持参考的模型")
            if roles & {"first_frame", "last_frame"} and roles & {"reference_image", "reference_audio", "reference_video"}:
                raise ProviderError("首尾帧与多模态参考不能混用于同一镜头")

    async def request(self, method, route, payload=None, *, timeout=180, task_id=None):
        b = self.binding
        headers = {"Authorization": f"Bearer {b.key}"} if b.key else {}
        try:
            response = await self.client.request(method, b.base_url + route, json=payload,
                                                 headers=headers, timeout=timeout)
        except httpx.RequestError as exc:
            before_send = isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout))
            unknown = method == "POST" and not before_send
            message = "模型服务连接中断；提交结果需要核对" if unknown else "未能建立模型服务连接；本次请求未发送" if before_send else "暂时无法查询模型服务"
            raise ProviderError(message, unknown=unknown, retryable=method == "GET" or before_send,
                                error_type=type(exc).__name__) from exc
        if response.status_code >= 400:
            code = response.status_code
            reason = {400: "请求参数不被服务接受", 401: "鉴权失败", 402: "账户余额或额度不足",
                      403: "没有模型权限", 404: "接口或模型不存在", 422: "内容或参数被拒绝",
                      410: "服务已停止向当前账号开放此接口", 429: "服务请求过于频繁"}.get(code, "服务暂时不可用")
            # Provider bodies may echo prompts, URLs, or auth; expose only safe classification.
            raise ProviderError(f"{reason}（HTTP {code}）", unknown=method == "POST" and code >= 500,
                                retryable=code == 429 or (method == "GET" and code >= 500), status_code=code)
        try:
            result = response.json()
        except ValueError as exc:
            raise ProviderError("服务返回无法解析的回执", unknown=method == "POST") from exc
        terminal_task = (method == "GET" and task_id is not None and result.get("id") == task_id
                         and result.get("status") in {"failed", "cancelled", "expired"})
        if result.get("base_resp", {}).get("status_code", 0) != 0 or (result.get("error") and not terminal_task):
            safe_code = str(result.get("base_resp", {}).get("status_code", "rejected"))[:20]
            raise ProviderError(f"模型服务拒绝请求（{safe_code}），请核对模型权限与参数")
        return result

    async def submit(self, purpose, args):
        self.validate(purpose, {k: v for k, v in args.items() if k not in {"prompt", "references"}}, args.get("references", []))
        b = self.binding
        if purpose in {"video", "videoFallback"}:
            return await self._video(args)
        if purpose == "image" and b.protocol in {"ark", "openai"}:
            body = {"model": b.model, "prompt": args["prompt"],
                    "size": args.get("size", "2K" if b.protocol == "ark" else "1536x1024")}
            if b.protocol == "ark":
                body.update(response_format="url", watermark=True)
                if args.get("references"):
                    body["image"] = [r["url"] for r in args["references"]]
            elif args.get("references"):
                raise ProviderError("该 OpenAI 图像生成适配器未实现参考图编辑，请选择支持参考图的连接")
            result = await self.request("POST", "/images/generations", body)
            items = result.get("data", [])
            if not items:
                raise ProviderError("服务未返回图片", unknown=True)
            if items[0].get("b64_json"):
                return MediaResult("succeeded", data=base64.b64decode(items[0]["b64_json"]),
                                   extension=".png", usage=result.get("usage", {}))
            urls = [x["url"] for x in items if x.get("url")]
            if not urls:
                raise ProviderError("图片回执缺少下载地址", unknown=True)
            return MediaResult("succeeded", urls=urls, extension=".png", usage=result.get("usage", {}))
        if b.protocol == "minimax_audio" and purpose == "voice":
            voice = args.get("voice_id")
            if not voice:
                raise ProviderError("配音需要从可用系统音色中选择 voice_id")
            body = {"model": b.model, "text": args["prompt"], "stream": False,
                    "voice_setting": {"voice_id": voice, "speed": args.get("speed", 1), "vol": 1},
                    "audio_setting": {"sample_rate": 32000, "format": "wav", "channel": 1},
                    "subtitle_enable": True, "output_format": "hex"}
            if args.get("emotion"):
                body["voice_setting"]["emotion"] = args["emotion"]
            result = await self.request("POST", "/t2a_v2", body)
            audio = result.get("data", {}).get("audio")
            if not audio:
                raise ProviderError("配音回执没有声音文件", unknown=True)
            return MediaResult("succeeded", data=bytes.fromhex(audio), extension=".wav",
                               subtitles=result.get("data", {}).get("subtitle_file"),
                               usage=result.get("extra_info", {}))
        if b.protocol == "minimax_audio" and purpose == "music":
            result = await self.request("POST", "/music_generation", {"model": b.model,
                "prompt": args["prompt"], "is_instrumental": True, "output_format": "hex",
                "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"}}, timeout=300)
            audio = result.get("data", {}).get("audio")
            if not audio:
                raise ProviderError("音乐回执没有声音文件", unknown=True)
            return MediaResult("succeeded", data=bytes.fromhex(audio), extension=".mp3",
                               usage=result.get("extra_info", {}))
        raise ProviderError("所选连接尚未实现此用途，请调整模型用途或接口类型")

    async def _video(self, args):
        b = self.binding
        content = [{"type": "text", "text": args["prompt"]}]
        refs = args.get("references", [])
        roles = {r["role"] for r in refs}
        if roles & {"first_frame", "last_frame"} and roles & {"reference_image", "reference_video", "reference_audio"}:
            raise ProviderError("首尾帧与多模态参考不能混用于同一镜头")
        for ref in refs:
            media_type = {"reference_audio": "audio_url", "reference_video": "video_url"}.get(ref["role"], "image_url")
            content.append({"type": media_type, media_type: {"url": ref["url"]}, "role": ref["role"]})
        duration = int(args.get("duration", 10))
        if b.protocol == "minimax_video":
            body = {"model": b.model, "content": content, "duration": duration,
                    "resolution": args.get("resolution", "768P"), "ratio": "16:9"}
            result = await self.request("POST", "/video_generation", body)
            task_id = result.get("task_id")
        elif b.protocol == "ark":
            body = {"model": b.model, "content": content, "duration": duration,
                    "resolution": args.get("resolution", "720p"), "ratio": "16:9", "generate_audio": True}
            result = await self.request("POST", "/contents/generations/tasks", body)
            task_id = result.get("id")
        else:
            raise ProviderError("此连接没有已实现的视频协议适配器")
        if not task_id:
            raise ProviderError("提交回执缺少任务 ID，请核对服务端任务记录", unknown=True)
        return MediaResult("queued", external_id=str(task_id))

    async def query(self, external_id):
        if not external_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError("非法外部任务身份")
        b = self.binding
        if b.protocol == "minimax_video":
            result = await self.request("GET", "/query/video_generation/" + external_id)
            result = result.get("task", result)
        elif b.protocol == "ark":
            result = await self.request("GET", "/contents/generations/tasks/" + external_id, task_id=external_id)
        else:
            raise ProviderError("该接口没有任务查询能力")
        state = result.get("status", "unknown").lower()
        state = {"success": "succeeded", "processing": "running", "pending": "queued"}.get(state, state)
        content = result.get("content") or {}
        url = content.get("url") or content.get("video_url") or result.get("video_url")
        if state == "succeeded" and not url:
            raise ProviderError("任务已完成但回执缺少视频地址")
        error = result.get("error") or {}
        code = str(error.get("code", "")) if isinstance(error, dict) else ""
        failure = ("content_policy" if "SensitiveContentDetected" in code or "PolicyViolation" in code
                   else "provider_generation_failed") if state == "failed" else None
        return MediaResult(state, external_id, urls=[url] if url else [], usage=result.get("usage", {}), failure_code=failure)

    async def discover(self):
        if self.binding.protocol in {"openai", "ark"}:
            result = await self.request("GET", "/models")
            return {"models": [{"id": m["id"]} for m in result.get("data", []) if m.get("id")],
                    "message": "模型列表查询成功；具体生成能力需分别验证"}
        if self.binding.protocol == "minimax_video":
            await self.request("GET", "/query/video_generation")
            return {"models": [], "message": "任务列表只读查询成功；请手动填写模型 ID，未验证生成权限"}
        if self.binding.protocol == "minimax_audio":
            result = await self.request("POST", "/get_voice", {"voice_type": "system"})
            voices = result.get("system_voice") or result.get("data", {}).get("system_voice") or []
            return {"models": [], "voices": voices, "message": "系统音色查询成功；未生成音频"}
        raise ProviderError("尚无此专用接口的连接检查器")


async def media_proxy(url: str):
    """Validate output routing, including Windows proxy fake-DNS for known provider CDNs."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.hostname:
        raise ProviderError("服务返回了不受支持的媒体地址")
    try:
        if not ipaddress.ip_address(parsed.hostname).is_global:
            raise ProviderError("媒体地址不能指向本地网络")
    except ValueError:
        if parsed.hostname in {"localhost"} or parsed.hostname.endswith(".local"):
            raise ProviderError("媒体地址不能指向本机")
    addresses = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    ips = [ipaddress.ip_address(item[4][0]) for item in addresses]
    if ips and all(ip.is_global for ip in ips):
        return None
    # Clash-style fake DNS is a synthetic address map, not the destination. Only
    # these observed provider output hosts may use the user's explicit loopback
    # HTTPS proxy for remote DNS + TLS. Never allow private origins or arbitrary hosts.
    proxy = getproxies().get("https")
    proxy = proxy if not proxy or "://" in proxy else "http://" + proxy
    trusted_hosts = {"algeng-video-infer.oss-cn-shanghai.aliyuncs.com", "ark-acg-cn-beijing.tos-cn-beijing.volces.com"}
    if (proxy and urlsplit(proxy).scheme in {"http", "https"} and urlsplit(proxy).hostname in {"127.0.0.1", "localhost"}
            and parsed.hostname in trusted_hosts and parsed.port in {None, 443}
            and ips and all(ip in ipaddress.ip_network("198.18.0.0/15") for ip in ips)):
        return proxy
    raise ProviderError("媒体域名解析到本地或保留网络，已拒绝下载")


async def download_media(client: httpx.AsyncClient, url: str, destination: Path):
    """Fetch provider output without forwarding any API credential."""
    proxy = await media_proxy(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    async def fetch(selected):
        async with selected.stream("GET", url, timeout=180, follow_redirects=False) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                async for chunk in response.aiter_bytes():
                    output.write(chunk)
    if proxy:
        async with httpx.AsyncClient(proxy=proxy, trust_env=False) as proxied:
            await fetch(proxied)
    else:
        await fetch(client)
    temporary.replace(destination)
