import asyncio

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
    assert next(s for s in streams if s["codec_type"] == "audio")["sample_rate"] == "48000"
