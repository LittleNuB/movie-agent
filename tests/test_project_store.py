from movie_agent.store import Store


def test_saving_and_submitting_hand_edit_preserves_adopted_script(tmp_path):
    store = Store(tmp_path)
    project = store.create_project("测试影片")
    script = store.create_artifact(project["id"], "script", "原剧本", "原稿")
    store.adopt(project["id"], script["id"], expected=None)
    store.save_draft(project["id"], "用户写的新结尾", expected_revision=0)
    submitted = store.submit_draft(project["id"], expected_revision=1)
    snapshot = Store(tmp_path).snapshot(project["id"])
    assert snapshot["project"]["adopted"]["script"] == script["id"]
    assert snapshot["project"]["draft"]["text"] == "用户写的新结尾"
    assert submitted["text"] == "用户写的新结尾"
    assert submitted["meta"]["manual"] is True
    assert snapshot["jobs"] == []
