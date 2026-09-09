"""Controlled structural and submission tests; no model quality evidence or paid requests."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from movie_agent.config import Binding, Configuration
from movie_agent.film_tools import FilmTools
from movie_agent.jobs import Jobs
from movie_agent.preproduction import Preproduction, ProductionBrief, ReferenceManifest, ShotSpec
from movie_agent.store import Conflict, Store


@pytest.fixture
def world(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project(mode="auto")["id"]
    script = store.create_artifact(pid, "script", "测试剧本", "主角关闸，让电机停转，同伴脱困但照明熄灭。")
    store.adopt(pid, script["id"], None)
    pre = Preproduction(store)
    data = {"script_id": script["id"], "entities": [
        {"id": "C1", "kind": "character", "name": "工程师", "description": "蓝色工作服", "origin": "script"}],
        "events": [{"id": "E1", "entity_ids": ["C1"], "motivation": "同伴被夹住", "preconditions": "总闸控制电机",
                    "action": "拉下总闸", "result": "同伴脱困", "state_before": "通电、门被卡住",
                    "state_after": "断电、失去照明", "audience_information": "救援的代价是失去照明",
                    "screen_expression": "拉闸动作、电机停声、灯熄灭", "source_location": "第二场"}]}
    brief = pre.publish_brief(pid, "制作说明", ProductionBrief.model_validate(data), "director")
    path = tmp_path / "media" / "image.png"
    path.parent.mkdir()
    path.write_bytes(b"controlled file-presence fixture, not a generated image")
    image = store.create_artifact(pid, "image", "测试身份图", path="media/image.png")
    run = store.put_record(pid, "runs", {"role": "visual_evidence", "status": "completed",
                                          "evidence": [{"artifact_id": image["id"], "time": None}]})
    evidence = store.create_artifact(pid, "continuity_check", "受控观察回执", "测试夹具，不代表真实视觉检查。",
                                     {"run_id": run["id"], "evidence": run["evidence"]})
    store.update_record(run["id"], artifact_id=evidence["id"])
    manifest_data = {"brief_id": brief["id"], "entries": [{"id": "REF1", "artifact_id": image["id"],
        "entity_ids": ["C1"], "purpose": "身份", "story_state": "关闸前", "view": "正面",
        "status": "standard", "evidence_ids": [evidence["id"]], "assessment": "仅验证观察身份与引用绑定"}]}
    manifest = pre.publish_manifest(pid, "参考清单", ReferenceManifest.model_validate(manifest_data), "visual")
    spec = {"brief_id": brief["id"], "manifest_id": manifest["id"], "unit_id": "SH1", "event_ids": ["E1"],
        "entity_ids": ["C1"], "intent": "说明救援行动的代价", "story_state": "关闸前、衣着未变",
        "start_frame": "工程师站在闸前", "end_frame": "闸落下、灯熄灭", "action": "拉下总闸",
        "camera": "固定中景", "sound": "电机停声，无背景音乐", "path": "multimodal",
        "path_reason": "保留主角身份，动作由文本指定",
        "references": [{"entry_id": "REF1", "role": "reference_image", "controls": "保持主角身份与服装"}]}
    binding = Binding(connection_id="test", protocol="minimax_video", base_url="https://example.test/v1",
                      model="MiniMax-H3", key="not-a-real-key", parameters={})
    return SimpleNamespace(store=store, pid=pid, pre=pre, data=data, brief=brief, script=script,
                           image=image, manifest=manifest, manifest_data=manifest_data, spec=spec, binding=binding)


def compile_input(w):
    return w.pre.compile(w.pid, "镜头输入", ShotSpec.model_validate(w.spec), "video", w.binding,
                         {"duration": 5, "resolution": "768P"}, None, "visual")


def test_documents_keep_drafts_and_adoption_separate_and_reopen(world):
    w = world
    assert w.store.project(w.pid)["adopted"] == {"script": w.script["id"]}
    assert w.store.project(w.pid)["draft"]["revision"] == 0
    assert w.store.records(w.pid, "jobs") == []
    assert Store(w.store.root).record(w.brief["id"])["meta"]["brief"]["events"][0]["action"] == "拉下总闸"
    w.data["events"][0]["entity_ids"] = ["missing"]
    with pytest.raises(ValueError, match="不存在"):
        w.pre.publish_brief(w.pid, "坏引用", ProductionBrief.model_validate(w.data), "director")


def test_reference_identity_cannot_be_faked_or_cross_projects(world):
    w = world
    entry = w.manifest_data["entries"][0]
    entry["parent_asset_ids"] = [w.image["id"]]
    with pytest.raises(ValueError, match="派生来源"):
        w.pre.publish_manifest(w.pid, "假派生", ReferenceManifest.model_validate(w.manifest_data), "visual")
    entry["parent_asset_ids"] = []
    other = w.store.create_project()["id"]
    foreign = w.store.create_artifact(other, "image", "另一项目", path=w.image["path"])
    entry["artifact_id"] = foreign["id"]
    with pytest.raises(KeyError):
        w.pre.publish_manifest(w.pid, "跨项目", ReferenceManifest.model_validate(w.manifest_data), "visual")


def test_standard_requires_actual_inspection_record_but_candidate_can_be_saved(world):
    w = world
    fake = w.store.create_artifact(w.pid, "continuity_check", "未经观察的意见", "看起来很好",
                                    {"evidence": [{"artifact_id": w.image["id"]}]})
    entry = w.manifest_data["entries"][0]
    entry["evidence_ids"] = [fake["id"]]
    with pytest.raises(ValueError, match="inspect_media"):
        w.pre.publish_manifest(w.pid, "假证据", ReferenceManifest.model_validate(w.manifest_data), "visual")
    entry.update(status="candidate", evidence_ids=[])
    candidate = w.pre.publish_manifest(w.pid, "候选", ReferenceManifest.model_validate(w.manifest_data), "visual")
    w.spec["manifest_id"] = candidate["id"]
    with pytest.raises(ValueError, match="先检查"):
        compile_input(w)


def test_compiler_uses_exact_assets_and_no_secret_or_external_call(world):
    w = world
    compiled = compile_input(w)
    meta = compiled["meta"]
    assert meta["references"] == [{"artifact_id": w.image["id"], "role": "reference_image"}]
    assert "图片1用途：保持主角身份与服装" in meta["prompt"]
    assert "电机停声，无背景音乐" in meta["prompt"]
    assert meta["brief_id"] == w.brief["id"]
    assert "not-a-real-key" not in json.dumps(compiled)
    assert w.store.records(w.pid, "jobs") == []


def test_input_modes_and_missing_reference_explanation(world):
    w = world
    w.spec["path"] = "frames"
    with pytest.raises(ValueError, match="帧路径"):
        compile_input(w)
    w.spec.update(path="text", references=[])
    with pytest.raises(ValueError, match="选择理由"):
        compile_input(w)
    w.spec["no_reference_reason"] = "远景中人物不可辨认，此镜头先验证场景变化"
    assert compile_input(w)["meta"]["references"] == []


def test_stale_brief_and_wrong_event_are_rejected_without_overwriting(world):
    w = world
    w.spec["event_ids"] = ["invented"]
    with pytest.raises(ValueError, match="镜头事件"):
        compile_input(w)
    w.spec["event_ids"] = ["E1"]
    newer = w.store.create_artifact(w.pid, "script", "新的用户决定", "保留手改")
    w.store.adopt(w.pid, newer["id"], w.script["id"])
    with pytest.raises(Conflict, match="过时"):
        compile_input(w)
    assert w.store.record(w.brief["id"])["meta"]["basis"]["script"] == w.script["id"]
    assert w.store.record(newer["id"])["text"] == "保留手改"


def configuration(w):
    return SimpleNamespace(binding=lambda purpose: w.binding, video_parameters=Configuration.video_parameters,
                           public=dict, vault=SimpleNamespace(get=lambda cid: w.binding.key),
                           connection=lambda cid: {"no_key": False})


async def test_agent_tools_preserve_review_and_compiled_submission(world):
    w = world
    jobs = Jobs(w.store, configuration(w), None)
    try:
        film = FilmTools(w.store, configuration(w), None, jobs, None)
        tools = {tool.name: tool for tool in film.for_agent(w.pid, "director")}
        # Nested Pydantic input schema is actually exposed to the model.
        assert "events" in json.dumps(tools["publish_production_brief"].input_schema)
        created = await tools["compile_shot_input"](title="工具编译", spec=w.spec, purpose="video",
            expected_model=w.binding.model, parameters={"duration": 5, "resolution": "768P"})
        compiled = json.loads(created.content[0].text)
        assert compiled["kind"] == "shot_input"
        blocked = await tools["submit_shot_input"](shot_input_id=compiled["id"], title="镜头", request_key="shot1",
                                                   stage="trial", basis_id=compiled["id"])
        assert blocked.state == "error" and w.store.records(w.pid, "jobs") == []
        visual = w.store.create_artifact(w.pid, "visual_plan", "已批准视觉")
        w.store.adopt(w.pid, visual["id"], None)
        result = await tools["submit_shot_input"](shot_input_id=compiled["id"], title="镜头", request_key="shot1",
                                                  stage="trial", basis_id=compiled["id"])
        job = json.loads(result.content[0].text)
        assert job["args"]["references"] == compiled["meta"]["references"]
        assert job["args"]["shot_input_id"] == compiled["id"]
        assert job["args"]["prompt"] == compiled["meta"]["prompt"]
        w.store.stop(w.pid)
        stopped = await tools["submit_shot_input"](shot_input_id=compiled["id"], title="镜头", request_key="shot2",
                                                   stage="trial", basis_id=compiled["id"])
        assert stopped.state == "error" and len(w.store.records(w.pid, "jobs")) == 1
    finally:
        await jobs.close()


async def test_queued_input_rechecks_basis_before_provider_send(world):
    w = world
    compiled = compile_input(w)
    meta = compiled["meta"]
    args = {key: meta[key] for key in ("prompt", "parameters", "references", "unit_id")}
    args.update(shot_input_id=compiled["id"], expected_model=w.binding.model, stage="trial", basis_id=compiled["id"])
    jobs = Jobs(w.store, configuration(w), None)
    try:
        job = await jobs.submit(w.pid, "video", "等待中的镜头", "queued", args)
        newer = w.store.create_artifact(w.pid, "script", "新剧本")
        w.store.adopt(w.pid, newer["id"], w.script["id"])
        # Even without FilmTools' outer gate the queued production binding must be checked.
        await jobs._run(job["id"])
        saved = w.store.record(job["id"])
        assert saved["status"] == "failed" and "过时" in saved["error"]
        assert saved["external_id"] is None and saved["started"] is None
    finally:
        await jobs.close()


def test_changed_prompt_and_provider_cannot_reuse_compilation(world):
    w = world
    compiled = compile_input(w)
    meta = compiled["meta"]
    args = {key: meta[key] for key in ("prompt", "parameters", "references", "unit_id")}
    args["expected_model"] = w.binding.model
    with pytest.raises(Conflict, match="连接已改变"):
        w.pre.verify_submission(w.pid, compiled["id"], args, "video", replace(w.binding, connection_id="other"))
    args["prompt"] = "改成另一场戏"
    with pytest.raises(Conflict, match="不一致"):
        w.pre.verify_submission(w.pid, compiled["id"], args, "video", w.binding)


async def test_compiled_references_reach_provider_and_returned_media_keeps_lineage(world, monkeypatch):
    from movie_agent.providers import MediaResult, Provider

    w = world
    compiled = compile_input(w)
    meta = compiled["meta"]
    args = {key: meta[key] for key in ("prompt", "parameters", "references", "unit_id")}
    args.update(shot_input_id=compiled["id"], expected_model=w.binding.model, stage="trial", basis_id=compiled["id"])
    received = []

    async def controlled_submit(provider, purpose, payload):
        received.append(payload)
        return MediaResult(state="succeeded", data=b"controlled output, not a real generated video", extension=".mp4")

    class MediaFixture:
        def source(self, aid, pid):
            asset = w.store.record(aid, pid, "artifacts")
            return asset, w.store.media_path(asset["path"])

        async def probe(self, path):
            return {"duration": 5, "streams": []}

    monkeypatch.setattr(Provider, "submit", controlled_submit)
    jobs = Jobs(w.store, configuration(w), MediaFixture())
    try:
        job = await jobs.submit(w.pid, "video", "受控提交", "transmission", args)
        await jobs._run(job["id"])
        assert len(received) == 1
        assert received[0]["prompt"] == meta["prompt"]
        assert received[0]["references"][0]["url"].startswith("data:image/png;base64,")
        assert received[0]["references"][0]["role"] == "reference_image"
        saved = w.store.record(job["id"])
        assert saved["status"] == "succeeded"
        video = w.store.record(saved["artifact_ids"][0])
        assert video["meta"]["shot_input_id"] == compiled["id"]
        assert video["meta"]["references"] == meta["references"]
    finally:
        await jobs.close()
