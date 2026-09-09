import json

import pytest

from movie_agent.film_tools import FilmTools
from movie_agent.store import Conflict, Store


def test_retired_audio_mode_preserves_history_and_requires_co_creation_review(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    script = store.create_artifact(pid, "script", "Existing script", "Keep this story")
    store.adopt(pid, script["id"], None)
    store.save_draft(pid, "Keep hand edits", 0)
    legacy_review = store.put_record(pid, "reviews", {
        "mode": "audio", "status": "approved", "kind": "script", "artifact_id": script["id"]})
    original = store.project(pid)
    # Seed an older database, bypassing the current write API only in this fixture.
    with store.connect() as con:
        con.execute("UPDATE projects SET body=? WHERE id=?", (json.dumps({**original, "mode": "audio"}), pid))
    store = Store(tmp_path)
    migrated = store.project(pid)
    assert migrated["mode"] == "co"
    assert {k: v for k, v in migrated.items() if k not in {"mode", "updated"}} == {
        k: v for k, v in original.items() if k not in {"mode", "updated"}}
    assert store.record(legacy_review["id"]) == legacy_review
    assert store.records(pid, "inputs") == []
    with store.connect() as con:
        event_count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    store = Store(tmp_path)
    with store.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == event_count
    film = FilmTools(store, None, None, None, None)
    with pytest.raises(Conflict):
        film.check_gate(pid, "production", "voice", script["id"])
    edit = store.create_artifact(pid, "edit_plan", "Replace music", meta={"scope": "audio"})
    review = film.request_review(pid, edit["id"], "Confirm music change")
    assert review["status"] == "pending"
    assert "edit_plan" not in store.project(pid)["adopted"]
    for mode in ["audio", "unknown"]:
        with pytest.raises(ValueError):
            store.create_project(mode=mode)
        with pytest.raises(ValueError):
            store.update_project(pid, mode=mode)


def test_auto_mode_still_approves_audio_edit_plan(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project(mode="auto")["id"]
    edit = store.create_artifact(pid, "edit_plan", "Replace music", meta={"scope": "audio"})
    review = FilmTools(store, None, None, None, None).request_review(pid, edit["id"], "Apply change")
    assert review["status"] == "approved"
    assert store.project(pid)["adopted"]["edit_plan"] == edit["id"]


async def test_export_only_keeps_source_dialogue_and_subtitles_without_rebuilding_timeline(tmp_path):
    from test_api_boundary import MemoryVault

    from movie_agent.config import Configuration
    from movie_agent.jobs import Jobs
    from movie_agent.media import Media
    store = Store(tmp_path)
    pid = store.create_project(mode="auto")["id"]
    edit = {"clips": [{"artifact_id": "scene-1", "duration": 90}],
            "tracks": [{"artifact_id": "independent-dialogue", "start": 27.8, "duration": 0.64}],
            "subtitles": [{"start": 27.8, "end": 28.5, "text": "爸"}]}
    source = store.create_artifact(pid, "film", "Original", meta={"edit": edit, "picture_master_id": "original-master"}, path="media/source.mp4")
    store.adopt(pid, source["id"], None)
    plan = store.create_artifact(pid, "edit_plan", "Change export resolution only")
    store.adopt(pid, plan["id"], None)
    config = Configuration(store, MemoryVault())
    media = Media(store)
    jobs = Jobs(store, config, media)
    film = FilmTools(store, config, None, jobs, media)
    export = next(t for t in film.for_agent(pid, "director") if t.name == "export_film_version")
    result = await export(source_film_id=source["id"], title="720P", request_key="derive1", basis_id=plan["id"])
    job = json.loads(result.content[0].text)
    assert job["purpose"] == "compose"
    assert all(job["args"][field] == edit[field] for field in ["clips", "tracks", "subtitles"])
    assert job["args"]["source_film_id"] == source["id"]
    assert store.record(source["id"])["meta"]["edit"] == edit
    await jobs.close()


def test_video_cannot_use_the_reference_image_stage_to_skip_visual_review(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    script = store.create_artifact(pid, "script", "Approved script")
    store.adopt(pid, script["id"], None)
    film = FilmTools(store, None, None, None, None)
    with pytest.raises(Conflict):
        film.check_gate(pid, "visual", "video", script["id"])


def test_historical_trial_restores_its_actual_basis(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    old = store.create_artifact(pid, "script", "Old")
    old_visual = store.create_artifact(pid, "visual_plan", "Old visual", meta={"basis": {"script": old["id"]}})
    trial = store.create_artifact(pid, "trial", "Old trial", meta={"basis": {"script": old["id"], "visual_plan": old_visual["id"]}})
    new = store.create_artifact(pid, "script", "New")
    store.adopt(pid, new["id"], None)
    store.adopt(pid, trial["id"], None, restore_basis=True)
    adopted = store.project(pid)["adopted"]
    assert adopted["script"] == old["id"] and adopted["visual_plan"] == old_visual["id"]


async def test_late_specialist_document_keeps_original_script_basis(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    old = store.create_artifact(pid, "script", "Old script")
    store.adopt(pid, old["id"], None)
    film = FilmTools(store, None, None, None, None)
    tools = film.for_agent(pid, "visual", {"script": old["id"]})
    new = store.create_artifact(pid, "script", "New script")
    store.adopt(pid, new["id"], old["id"])
    publish = next(t for t in tools if t.name == "publish_document")
    result = await publish(kind="shot_plan", title="Old work returned late", text="Old shots", data={})
    artifact = json.loads(result.content[0].text)
    assert artifact["meta"]["basis"]["script"] == old["id"]
    assert artifact["meta"]["candidate_only"] is True
    with pytest.raises(Conflict):
        film.check_gate(pid, "trial", "video", artifact["id"])


async def test_late_visual_revision_cannot_replace_new_visual_on_the_same_script(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project(mode="auto")["id"]
    script = store.create_artifact(pid, "script", "Same script")
    store.adopt(pid, script["id"], None)
    image = store.create_artifact(pid, "image", "Controlled image identity", path="media/fixture.png")
    old = store.create_artifact(pid, "visual_plan", "Old visual")
    store.adopt(pid, old["id"], None)
    film = FilmTools(store, None, None, None, None)
    publish = next(t for t in film.for_agent(pid, "visual", store.project(pid)["adopted"]) if t.name == "publish_document")
    new = store.create_artifact(pid, "visual_plan", "New visual")
    store.adopt(pid, new["id"], old["id"])
    result = await publish(kind="visual_plan", title="Late revision", text="Old visual revision", data={"asset_ids": [image["id"]]})
    late = json.loads(result.content[0].text)
    with pytest.raises(Conflict):
        film.request_review(pid, late["id"], "Do not overwrite")
    assert store.project(pid)["adopted"]["visual_plan"] == new["id"]


def test_new_script_does_not_inherit_old_visual_and_trial_approvals(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    film = FilmTools(store, None, None, None, None)
    for kind in ["script", "visual_plan", "trial"]:
        artifact = store.create_artifact(pid, kind, kind)
        store.adopt(pid, artifact["id"], None)
    prior = store.project(pid)["adopted"]["script"]
    new = store.create_artifact(pid, "script", "New story")
    store.adopt(pid, new["id"], prior)
    with pytest.raises(Conflict):
        film.check_gate(pid, "production", "video", new["id"])
    assert len(store.records(pid, "artifacts")) == 4


def test_review_cannot_approve_assets_after_its_story_changed(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    film = FilmTools(store, None, None, None, None)
    script = store.create_artifact(pid, "script", "Original")
    store.adopt(pid, script["id"], None)
    image = store.create_artifact(pid, "image", "controlled image reference", path="media/fixture.png")
    visual = store.create_artifact(pid, "visual_plan", "Visuals", meta={"asset_ids": [image["id"]]})
    review = film.request_review(pid, visual["id"], "Review")
    newer = store.create_artifact(pid, "script", "New story")
    store.adopt(pid, newer["id"], script["id"])
    with pytest.raises(Conflict):
        film.decide_review(pid, review["id"], True)
    assert store.record(review["id"])["status"] == "pending"
    assert "visual_plan" not in store.project(pid)["adopted"]


def test_direct_basis_must_be_the_approved_script(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    film = FilmTools(store, None, None, None, None)
    approved = store.create_artifact(pid, "script", "Approved")
    store.adopt(pid, approved["id"], None)
    submitted = store.create_artifact(pid, "script", "Unapproved changes")
    with pytest.raises(Conflict):
        film.check_gate(pid, "visual", "image", submitted["id"])


def test_late_auto_film_cannot_restore_an_old_story(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project(mode="auto")["id"]
    film = FilmTools(store, None, None, None, None)
    old = store.create_artifact(pid, "script", "Old")
    store.adopt(pid, old["id"], None)
    new = store.create_artifact(pid, "script", "New")
    store.adopt(pid, new["id"], old["id"])
    late = store.create_artifact(pid, "film", "Late", meta={"basis": {"script": old["id"]}}, path="media/late.mp4")
    with pytest.raises(Conflict):
        film.request_review(pid, late["id"], "Adopt late result")
    assert store.project(pid)["adopted"]["script"] == new["id"]


def test_natural_language_review_records_exact_message_and_artifact(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    film = FilmTools(store, None, None, None, None)
    proposal = store.create_artifact(pid, "proposal", "Story proposal")
    review = film.request_review(pid, proposal["id"], "Approve this proposal?")
    message = store.accept_message(pid, "approval-message", "认可这个提案，继续写剧本。", [])
    decided = film.review_from_message(pid, review["id"], message["id"], True, "认可提案")
    assert decided["evidence_message_id"] == message["id"]
    assert decided["authority"] == "user_message"
    assert store.project(pid)["adopted"]["proposal"] == proposal["id"]


def test_button_review_commits_a_durable_input_and_is_idempotent(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    film = FilmTools(store, None, None, None, None)
    proposal = store.create_artifact(pid, "proposal", "Story proposal")
    review = film.request_review(pid, proposal["id"], "Approve?")
    film.decide_review(pid, review["id"], True)
    epoch = store.project(pid)["epoch"]
    assert store.record("review-" + review["id"])["status"] == "pending"
    film.decide_review(pid, review["id"], True)
    assert store.project(pid)["epoch"] == epoch
