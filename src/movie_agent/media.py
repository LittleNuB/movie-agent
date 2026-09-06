"""Actual FFmpeg editing, separate picture masters, and grounded frame inspection."""

import asyncio
import base64
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

from agentscope.message import Base64Source, DataBlock, Msg, TextBlock, UserMsg

from .store import uid


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
        audible_clips = {c["artifact_id"] for c in clips if seconds(c.get("audio_gain", 1)) > 0}
        for track in plan.get("tracks", []):
            if seconds(track.get("gain", 0.5)) == 0:
                continue
            artifact = self.store.record(track["artifact_id"], pid, "artifacts")
            meta = artifact.get("meta", {})
            mixed_clips = meta.get("edit", {}).get("clips", []) if artifact["kind"] in {"film", "trial"} else []
            if meta.get("purpose") == "native_mixed":
                mixed_clips = meta.get("clips", [])
                if not mixed_clips and meta.get("job_id"):
                    mixed_clips = self.store.record(meta["job_id"], pid, "jobs")["args"].get("clips", [])
            if audible_clips.intersection(c["artifact_id"] for c in mixed_clips):
                raise ValueError("混合音轨包含当前镜头已经播放的原生声音，叠加会重复。请选择镜头原生声加独立配音，或将对应镜头audio_gain设为0后复用完整混音；原生混合声不包含后来加入的独立台词。")
        duration = sum(seconds(c["duration"], 0.04) for c in clips)
        if plan["kind"] == "film" and not 90 <= duration <= 120:
            raise ValueError("完整影片镜头总长应为90–120秒，请调整剪辑计划，不能用空白凑时长")
        native_parts = []
        picture_parts = []
        source_conversions = []
        master_id = plan.get("picture_master_id")
        old_master = self.store.record(master_id, pid) if master_id else None
        requested_master_id = master_id
        if old_master:
            prior_clips = old_master.get("meta", {}).get("clips", [])
            compare = lambda rows: [(r["artifact_id"], float(r.get("start", 0)), float(r["duration"]),
                                     float(r.get("fade_in", 0)), float(r.get("fade_out", 0)), float(r.get("speed", 1))) for r in rows]
            if compare(clips) != compare(prior_clips):
                raise ValueError("镜头剪辑发生变化，不能沿用旧画面母版")
        for index, clip in enumerate(clips):
            _, source = self.source(clip["artifact_id"], pid)
            metadata = await self.probe(source)
            video_stream = next((s for s in metadata["streams"] if s["codec_type"] == "video"), {})
            source_conversions.append({"artifact_id": clip["artifact_id"], "source_width": video_stream.get("width"),
                "source_height": video_stream.get("height"), "output_width": 1280, "output_height": 720})
            start, length = seconds(clip.get("start", 0)), seconds(clip["duration"], 0.04)
            speed = seconds(clip.get("speed", 1), 0.25)
            if speed > 4:
                raise ValueError("基础变速范围为0.25–4倍")
            if start + length * speed > metadata["duration"] + 0.08:
                raise ValueError(f"镜头 {index + 1} 超出源素材时长")
            part = folder / f"picture_{index:03}.mp4"
            if not old_master:
                video_filter = f"setpts=(PTS-STARTPTS)/{speed},scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24"
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
                # atempo changes timing while preserving pitch; the original mixed
                # audio remains a mixed track, not fabricated dialogue/SFX stems.
                tempo = speed
                tempo_filters = []
                while tempo > 2:
                    tempo_filters.append("atempo=2")
                    tempo /= 2
                while tempo < 0.5:
                    tempo_filters.append("atempo=0.5")
                    tempo /= 0.5
                tempo_filters.append(f"atempo={tempo}")
                args = ["-ss", start, "-i", source, "-vn", "-af", ",".join(tempo_filters) + f",volume={gain},apad"]
            else:
                args = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            await self.execute([self.ffmpeg, "-v", "error", "-y", *args, "-t", length,
                                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", native], job_id=jid)
            native_parts.append(native)
        if old_master:
            _, picture = self.source(master_id, pid)
            metadata = await self.probe(picture)
            video_stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
            if (video_stream.get("width"), video_stream.get("height")) != (1280, 720):
                # Derive a new local master; never overwrite history or regenerate cloud shots.
                converted = folder / "picture-master-720p.mp4"
                await self.execute([self.ffmpeg, "-v", "error", "-y", "-i", picture, "-an", "-vf",
                    "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", converted], job_id=jid)
                picture = converted
                master = self.store.create_artifact(pid, "picture_master", job["title"] + " · 720P画面母版",
                    meta={"clips": clips, "duration": duration, "source_master_id": master_id, "resolution": "720p"},
                    path=picture.relative_to(self.store.root).as_posix())
                master_id = master["id"]
        else:
            listing = folder / "picture-list.txt"
            listing.write_text("\n".join(f"file '{p.name}'" for p in picture_parts), encoding="utf-8")
            picture = folder / "picture-master.mp4"
            await self.execute([self.ffmpeg, "-v", "error", "-y", "-f", "concat", "-safe", "1", "-i", listing,
                                "-c", "copy", "-movflags", "+faststart", picture], job_id=jid)
            master = self.store.create_artifact(pid, "picture_master", job["title"] + " · 画面母版",
                meta={"clips": clips, "duration": duration, "resolution": "720p"}, path=picture.relative_to(self.store.root).as_posix())
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
            audio_info = await self.probe(source)
            source_start = seconds(track.get("source_start", 0))
            if source_start >= audio_info["duration"]:
                raise ValueError("声音入点超出源素材时长")
            if track.get("loop"):
                command += ["-stream_loop", "-1"]
            if track.get("source_start"):
                command += ["-ss", seconds(track["source_start"])]
            if track.get("duration"):
                command += ["-t", seconds(track["duration"], 0.04)]
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
                audible_length = duration - offset / 1000 if track.get("loop") else min(audio_info["duration"] - source_start, duration - offset / 1000)
                if track.get("duration"):
                    audible_length = min(audible_length, seconds(track["duration"]))
                track_filter += f",afade=t=out:st={max(0,audible_length-fade)}:d={min(fade,audible_length)}"
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
            meta={"purpose": "native_mixed", "media": await self.probe(native), "job_id": jid, "clips": clips},
            path=native.relative_to(self.store.root).as_posix())
        return {"path": output.relative_to(self.store.root).as_posix(), "picture_master_id": master_id,
                "native_audio_id": native_artifact["id"],
                "native_audio_path": native.relative_to(self.store.root).as_posix(),
                "subtitle_path": srt.relative_to(self.store.root).as_posix() if subtitles else None,
                "vtt_path": (folder / "subtitles.vtt").relative_to(self.store.root).as_posix() if subtitles else None,
                "edit": plan, "media": info, "picture_sha256": hashlib.sha256(picture.read_bytes()).hexdigest(),
                "output_resolution": "720p", "source_conversions": source_conversions,
                "requested_master_id": requested_master_id}

    async def extract_frame(self, project_id, artifact_id, time, title):
        artifact, source = self.source(artifact_id, project_id)
        info = await self.probe(source)
        position = seconds(time)
        if not any(s["codec_type"] == "video" for s in info["streams"]) or position >= info["duration"]:
            raise ValueError("请指定视频内实际存在的帧位置")
        folder = self.store.root / "media" / "frames"
        folder.mkdir(parents=True, exist_ok=True)
        frame = folder / (uid() + ".jpg")
        await self.execute([self.ffmpeg, "-v", "error", "-y", "-ss", position, "-i", source, "-frames:v", "1", "-q:v", "2", frame])
        return self.store.create_artifact(project_id, "image", title,
            meta={"source_artifact_id": artifact["id"], "source_time": position, "media": await self.probe(frame)},
            path=frame.relative_to(self.store.root).as_posix())

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
                blocks.append(TextBlock(text=f"素材 {aid} 的实际容器元数据：{json.dumps(info, ensure_ascii=False)}。"
                    "下面图片是为检查而缩小的抽帧，不是原始生成或交付分辨率；不要根据抽帧尺寸推定源规格。"))
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
        run = self.store.put_record(project_id, "runs", {"role": "visual_evidence", "status": "running",
            "input_tokens": 0, "output_tokens": 0, "task": question, "evidence": evidence})
        text = ""
        try:
            async for event in agent.reply_stream(UserMsg("检查请求", blocks), yield_final_msg=True):
                if isinstance(event, Msg):
                    continue
                if str(event.type).lower() == "text_block_delta":
                    text += event.delta
                elif str(event.type).lower() == "model_call_end":
                    run = self.store.update_record(run["id"], input_tokens=run["input_tokens"] + event.input_tokens,
                                                   output_tokens=run["output_tokens"] + event.output_tokens)
        except Exception as exc:
            self.store.update_record(run["id"], status="failed", error_type=type(exc).__name__)
            raise
        result = self.store.create_artifact(project_id, "continuity_check", "媒体观察", text,
                                            {"evidence": evidence, "audio_review": "not_performed", "run_id": run["id"]})
        self.store.update_record(run["id"], status="completed", artifact_id=result["id"])
        return result
