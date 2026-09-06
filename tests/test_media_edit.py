import array
import asyncio
import math

import pytest

from movie_agent.media import Media
from movie_agent.store import Store


@pytest.mark.asyncio
async def test_replacing_audio_preserves_decoded_video_and_subtitle_timing(tmp_path):
    store = Store(tmp_path)
    media = Media(store)
    if not media.ffmpeg:
        pytest.skip("FFmpeg required for actual encode/decode test")
    pid = store.create_project()["id"]
    folder = tmp_path / "media" / "fixture"
    folder.mkdir(parents=True)
    video, tone_a, tone_b = folder / "source.mp4", folder / "tone-a.wav", folder / "tone-b.wav"
    await media.execute([media.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=24",
                         "-t", "2", "-c:v", "libx264", video])
    for path, frequency in [(tone_a, 220), (tone_b, 440)]:
        await media.execute([media.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration=2", path])
    src = store.create_artifact(pid, "video", "controlled video", path=video.relative_to(tmp_path).as_posix())
    audio = [store.create_artifact(pid, "audio", "controlled audio", path=f.relative_to(tmp_path).as_posix()) for f in [tone_a, tone_b]]
    plan = {"kind": "trial", "clips": [{"artifact_id": src["id"], "duration": 2, "start": 0}],
            "tracks": [{"artifact_id": audio[0]["id"], "start": 0, "gain": 0.4}],
            "subtitles": [{"start": 0.2, "end": 1.8, "text": "A subtitle"}]}
    before = await media.render({"id": "edit-before", "project_id": pid, "args": plan, "title": "Before"})
    after_plan = {**plan, "picture_master_id": before["picture_master_id"],
                  "tracks": [{"artifact_id": audio[1]["id"], "start": 0, "gain": 0.4}]}
    after = await media.render({"id": "edit-after", "project_id": pid, "args": after_plan, "title": "After"})
    async def decoded_hash(result, stream):
        return await media.execute([media.ffmpeg, "-v", "error", "-i", store.media_path(result["path"]),
                                    "-map", f"0:{stream}:0", "-f", "hash", "-hash", "sha256", "-"])
    video_hashes = await asyncio.gather(decoded_hash(before, "v"), decoded_hash(after, "v"))
    audio_hashes = await asyncio.gather(decoded_hash(before, "a"), decoded_hash(after, "a"))
    assert video_hashes[0] == video_hashes[1]
    assert audio_hashes[0] != audio_hashes[1]
    assert before["picture_master_id"] == after["picture_master_id"]
    assert store.media_path(before["vtt_path"]).read_text() == store.media_path(after["vtt_path"]).read_text()
    streams = after["media"]["streams"]
    assert next(s for s in streams if s["codec_type"] == "video")["r_frame_rate"] == "24/1"
    assert [(s["width"], s["height"]) for s in streams if s["codec_type"] == "video"] == [(1280, 720)]
    assert next(s for s in streams if s["codec_type"] == "audio")["sample_rate"] == "48000"


async def test_speed_consumes_the_right_source_span_and_short_audio_fades_before_it_ends(tmp_path):
    store = Store(tmp_path)
    media = Media(store)
    if not media.ffmpeg:
        pytest.skip("FFmpeg required")
    pid = store.create_project()["id"]
    folder = tmp_path / "media" / "fixture"
    folder.mkdir(parents=True)
    video, audio = folder / "source.mp4", folder / "short.wav"
    await media.execute([media.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=24",
                         "-t", "4", "-c:v", "libx264", video])
    await media.execute([media.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", audio])
    src = store.create_artifact(pid, "video", "controlled", path=video.relative_to(tmp_path).as_posix())
    tone = store.create_artifact(pid, "audio", "controlled", path=audio.relative_to(tmp_path).as_posix())
    result = await media.render({"id": "speed-fade", "project_id": pid, "title": "Controlled timing check", "args": {
        "kind": "trial", "clips": [{"artifact_id": src["id"], "start": 0, "duration": 2, "speed": 2}],
        "tracks": [{"artifact_id": tone["id"], "start": 0.5, "gain": 1, "fade_out": 0.5}]}})
    assert abs(result["media"]["duration"] - 2) < 0.1
    async def rms(start):
        raw = await media.execute([media.ffmpeg, "-v", "error", "-ss", start, "-i", store.media_path(result["path"]),
            "-t", "0.08", "-vn", "-ac", "1", "-ar", "48000", "-f", "s16le", "-"])
        values = array.array("h", raw)
        return math.sqrt(sum(v*v for v in values) / len(values))
    assert await rms(1.4) < (await rms(0.7)) * 0.3


async def test_old_high_resolution_master_is_derived_locally_without_overwriting_history(tmp_path):
    store = Store(tmp_path)
    media = Media(store)
    if not media.ffmpeg:
        pytest.skip("FFmpeg required")
    pid = store.create_project()["id"]
    folder = tmp_path / "media" / "old"
    folder.mkdir(parents=True)
    path = folder / "master.mp4"
    await media.execute([media.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=24",
                         "-t", "0.5", "-an", "-c:v", "libx264", "-preset", "ultrafast", path])
    prior_bytes = path.read_bytes()
    src = store.create_artifact(pid, "video", "Old source", path=path.relative_to(tmp_path).as_posix())
    clips = [{"artifact_id": src["id"], "duration": 0.5}]
    master = store.create_artifact(pid, "picture_master", "Old master", meta={"clips": clips}, path=src["path"])
    result = await media.render({"id": "derive-720", "project_id": pid, "title": "720P version", "args": {
        "kind": "trial", "clips": clips, "picture_master_id": master["id"]}})
    assert result["picture_master_id"] != master["id"]
    assert store.record(result["picture_master_id"])["meta"]["source_master_id"] == master["id"]
    assert [(s["width"], s["height"]) for s in result["media"]["streams"] if s["codec_type"] == "video"] == [(1280, 720)]
    assert path.read_bytes() == prior_bytes


async def test_reusing_native_mix_requires_disabling_duplicate_clip_audio(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    media = Media(store)
    media.ffmpeg = "unused-after-preflight-rejection"
    source = store.create_artifact(pid, "video", "Scene", path="media/source.mp4")
    mix = store.create_artifact(pid, "audio", "Native scene mix", meta={"purpose": "native_mixed", "clips": [{"artifact_id": source["id"]}]})
    with pytest.raises(ValueError, match="叠加会重复"):
        await media.render({"id": "duplicate-audio", "project_id": pid, "title": "Wrong audio reuse", "args": {
            "kind": "trial", "clips": [{"artifact_id": source["id"], "duration": 1}],
            "tracks": [{"artifact_id": mix["id"], "gain": 1}]}})
