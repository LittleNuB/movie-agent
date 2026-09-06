"""Actual FFmpeg editing, separate picture masters, and grounded frame inspection."""

import asyncio
import base64
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

from agentscope.message import Base64Source, DataBlock, TextBlock, UserMsg


def seconds(value, minimum=0):
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise ValueError("时间或音量参数不合法")
    return result


class Media:
    def __init__(self, store):
        self.store = store
        repo = Path(__file__).resolve().parents[2]
        candidates = list((repo / ".cache/tools/ffmpeg").glob("**/ffmpeg.exe"))
        self.ffmpeg = os.environ.get("MOVIE_FFMPEG") or shutil.which("ffmpeg") or (str(candidates[0]) if candidates else None)
        self.ffprobe = (str(Path(self.ffmpeg).with_name("ffprobe.exe")) if self.ffmpeg and os.name == "nt"
                        else shutil.which("ffprobe"))
        self.processes = {}

    async def execute(self, args, *, cwd=None, job_id=None):
        process = await asyncio.create_subprocess_exec(*[str(a) for a in args], cwd=cwd,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        if job_id:
            self.processes[job_id] = process
        try:
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                # Keep diagnostic output local, not mixed into chat or LLM context.
                if job_id:
                    (self.store.root / "media" / job_id / "ffmpeg-error.log").write_bytes(stderr[-16000:])
                raise ValueError("媒体处理失败，请检查本地任务诊断记录")
            return stdout
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
        finally:
            if job_id:
                self.processes.pop(job_id, None)

    async def probe(self, path):
        if not self.ffprobe:
            raise ValueError("FFmpeg 尚未配置，请运行 scripts/setup.ps1")
        output = await self.execute([self.ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", path])
        raw = json.loads(output)
        return {"duration": float(raw.get("format", {}).get("duration", 0)),
                "streams": [{k: s.get(k) for k in ["codec_type", "codec_name", "width", "height", "r_frame_rate", "sample_rate", "channels"]}
                            for s in raw.get("streams", [])]}

    def source(self, artifact_id, project_id):
        artifact = self.store.record(artifact_id, project_id)
        if not artifact.get("path"):
            raise ValueError("素材尚未生成")
        path = self.store.media_path(artifact["path"])
        if not path.is_file():
            raise ValueError("本地素材文件不存在")
        return artifact, path

    async def render(self, job):
        if not self.ffmpeg:
            raise ValueError("请先安装 FFmpeg")
        plan, pid, jid = job["args"], job["project_id"], job["id"]
        folder = self.store.root / "media" / jid
        folder.mkdir(parents=True, exist_ok=True)
        clips = plan["clips"]
        if not clips:
            raise ValueError("合成需要真实镜头")
        duration = sum(seconds(c["duration"], 0.04) for c in clips)
        if plan["kind"] == "film" and not 90 <= duration <= 120:
            raise ValueError("完整影片镜头总长应为90–120秒，请调整剪辑计划，不能用空白凑时长")
        native_parts = []
        picture_parts = []
        master_id = plan.get("picture_master_id")
        old_master = self.store.record(master_id, pid) if master_id else None
        if old_master:
            prior_clips = old_master.get("meta", {}).get("clips", [])
            compare = lambda rows: [(r["artifact_id"], float(r.get("start", 0)), float(r["duration"]),
                                     float(r.get("fade_in", 0)), float(r.get("fade_out", 0))) for r in rows]
            if compare(clips) != compare(prior_clips):
                raise ValueError("镜头剪辑发生变化，不能沿用旧画面母版")
        for index, clip in enumerate(clips):
            _, source = self.source(clip["artifact_id"], pid)
            metadata = await self.probe(source)
            start, length = seconds(clip.get("start", 0)), seconds(clip["duration"], 0.04)
            if start + length > metadata["duration"] + 0.08:
                raise ValueError(f"镜头 {index + 1} 超出源素材时长")
            part = folder / f"picture_{index:03}.mp4"
            if not old_master:
                video_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24"
                fade_in, fade_out = seconds(clip.get("fade_in", 0)), seconds(clip.get("fade_out", 0))
                if fade_in + fade_out > length:
                    raise ValueError("镜头淡入淡出超过片段时长")
                if fade_in:
                    video_filter += f",fade=t=in:st=0:d={fade_in}"
                if fade_out:
                    video_filter += f",fade=t=out:st={length-fade_out}:d={fade_out}"
                await self.execute([self.ffmpeg, "-v", "error", "-y", "-ss", start, "-i", source,
                    "-t", length, "-an", "-vf", video_filter,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", part], job_id=jid)
                picture_parts.append(part)
            native = folder / f"native_{index:03}.wav"
            gain = seconds(clip.get("audio_gain", 1))
            if any(s["codec_type"] == "audio" for s in metadata["streams"]):
                args = ["-ss", start, "-i", source, "-vn", "-af", f"volume={gain},apad"]
            else:
                args = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            await self.execute([self.ffmpeg, "-v", "error", "-y", *args, "-t", length,
                                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", native], job_id=jid)
            native_parts.append(native)
        if old_master:
            _, picture = self.source(master_id, pid)
        else:
            listing = folder / "picture-list.txt"
            listing.write_text("\n".join(f"file '{p.name}'" for p in picture_parts), encoding="utf-8")
            picture = folder / "picture-master.mp4"
            await self.execute([self.ffmpeg, "-v", "error", "-y", "-f", "concat", "-safe", "1", "-i", listing,
                                "-c", "copy", "-movflags", "+faststart", picture], job_id=jid)
            master = self.store.create_artifact(pid, "picture_master", job["title"] + " · 画面母版",
                meta={"clips": clips, "duration": duration}, path=picture.relative_to(self.store.root).as_posix())
            master_id = master["id"]
        listing = folder / "native-list.txt"
        listing.write_text("\n".join(f"file '{p.name}'" for p in native_parts), encoding="utf-8")
        native = folder / "native.wav"
        await self.execute([self.ffmpeg, "-v", "error", "-y", "-f", "concat", "-safe", "1", "-i", listing,
                            "-c:a", "pcm_s16le", native], job_id=jid)
        command = [self.ffmpeg, "-v", "error", "-y", "-i", picture, "-i", native]
        filters, labels = [], ["[1:a]"]
        for index, track in enumerate(plan.get("tracks", []), start=2):
            _, source = self.source(track["artifact_id"], pid)
            if track.get("loop"):
                command += ["-stream_loop", "-1"]
            command += ["-i", source]
            offset = int(seconds(track.get("start", 0)) * 1000)
            if offset >= duration * 1000:
                raise ValueError("声音开始时间超出影片时长")
            gain = seconds(track.get("gain", 0.5))
            track_filter = f"[{index}:a]aresample=48000,volume={gain}"
            if track.get("fade_in"):
                track_filter += f",afade=t=in:st=0:d={seconds(track['fade_in'])}"
            if track.get("fade_out"):
                fade = seconds(track["fade_out"])
                track_filter += f",afade=t=out:st={max(0,duration-offset/1000-fade)}:d={fade}"
            filters.append(track_filter + f",adelay={offset}:all=1[a{index}]")
            labels.append(f"[a{index}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95[mix]")
        command += ["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[mix]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", duration]
        subtitles = plan.get("subtitles", [])
        srt = folder / "subtitles.srt"
        if subtitles:
            def timestamp(value):
                ms = round(seconds(value) * 1000)
                return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
            for cue in subtitles:
                if not 0 <= seconds(cue["start"]) < seconds(cue["end"]) <= duration + 0.05:
                    raise ValueError("字幕时间超出成片或顺序不合法")
            srt.write_text("\n\n".join(f'{i}\n{timestamp(c["start"])} --> {timestamp(c["end"])}\n{c["text"]}'
                                      for i, c in enumerate(subtitles, 1)), encoding="utf-8")
            (folder / "subtitles.vtt").write_text("WEBVTT\n\n" + "\n\n".join(
                f'{timestamp(c["start"]).replace(",", ".")} --> {timestamp(c["end"]).replace(",", ".")}\n{c["text"]}'
                for c in subtitles), encoding="utf-8")
        output = folder / "film.mp4"
        # A selectable subtitle stream preserves an exact reusable picture master.
        if subtitles:
            input_insert = command.index("-filter_complex")
            command[input_insert:input_insert] = ["-i", srt]
            command += ["-map", f"{2 + len(plan.get('tracks', []))}:0", "-c:s", "mov_text",
                        "-metadata:s:s:0", "language=zho", "-disposition:s:0", "default"]
        command += ["-movflags", "+faststart", output]
        await self.execute(command, job_id=jid)
        info = await self.probe(output)
        native_artifact = self.store.create_artifact(pid, "audio", job["title"] + " · 原生混合声",
            meta={"purpose": "native_mixed", "media": await self.probe(native), "job_id": jid},
            path=native.relative_to(self.store.root).as_posix())
        return {"path": output.relative_to(self.store.root).as_posix(), "picture_master_id": master_id,
                "native_audio_id": native_artifact["id"],
                "native_audio_path": native.relative_to(self.store.root).as_posix(),
                "subtitle_path": srt.relative_to(self.store.root).as_posix() if subtitles else None,
                "vtt_path": (folder / "subtitles.vtt").relative_to(self.store.root).as_posix() if subtitles else None,
                "edit": plan, "media": info, "picture_sha256": hashlib.sha256(picture.read_bytes()).hexdigest()}

    async def inspect(self, project_id, artifact_ids, question, runtime):
        if not 1 <= len(artifact_ids) <= 8:
            raise ValueError("单次视觉检查请选择1–8份素材，可分批检查整片")
        from agentscope.agent import Agent, ReActConfig
        blocks = [TextBlock(text=question + "\n只报告实际可见证据，抽帧不能证明完整运动、声音或整片质量。")]
        evidence = []
        folder = self.store.root / "media" / "inspection"
        folder.mkdir(parents=True, exist_ok=True)
        for aid in artifact_ids:
            artifact, source = self.source(aid, project_id)
            if source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                frames = [(0, source)]
            else:
                info = await self.probe(source)
                if not any(s["codec_type"] == "video" for s in info["streams"]):
                    raise ValueError("该视觉检查器不能直接听音频")
                positions = [0.2, max(0.2, info["duration"] / 2), max(0.2, info["duration"] - 0.25)]
                frames = []
                for index, position in enumerate(positions):
                    frame = folder / f"{aid}-{index}.jpg"
                    await self.execute([self.ffmpeg, "-v", "error", "-y", "-ss", position, "-i", source,
                                        "-frames:v", "1", "-vf", "scale=960:-2", frame])
                    frames.append((position, frame))
            for position, frame in frames:
                raw = frame.read_bytes()
                mime = "image/jpeg" if raw.startswith(b"\xff\xd8\xff") else "image/png" if raw.startswith(b"\x89PNG") else "image/webp"
                blocks += [TextBlock(text=f"素材 {aid}，标题 {artifact['title']}，时间 {position:.2f}s"),
                           DataBlock(source=Base64Source(data=base64.b64encode(raw).decode(), media_type=mime))]
                evidence.append({"artifact_id": aid, "time": position})
        agent = Agent("visual-evidence", "你是电影视觉检查者，以实际输入图像为依据，区分观察与推断。",
                      runtime.model("vision"), react_config=ReActConfig(max_iters=1))
        reply = await agent.reply(UserMsg("检查请求", blocks))
        text = "\n".join(b.text for b in reply.content if b.type == "text")
        result = self.store.create_artifact(project_id, "continuity_check", "媒体观察", text,
                                            {"evidence": evidence, "audio_review": "not_performed"})
        return result
