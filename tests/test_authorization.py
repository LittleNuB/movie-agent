import pytest

from movie_agent.film_tools import FilmTools
from movie_agent.store import Conflict, Store


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
