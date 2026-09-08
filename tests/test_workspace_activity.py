from types import SimpleNamespace

from fastapi.testclient import TestClient

from movie_agent.activity import close_activity, record_event
from movie_agent.api import create_app
from movie_agent.store import Store


def test_trace_distinguishes_preparation_execution_and_failure_without_arguments(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    run = store.put_record(pid, "runs", {"role": "visual", "status": "running"})
    record_event(store, pid, run, SimpleNamespace(type="tool_call_start", tool_call_id="call1", tool_call_name="generate_media", input="private-argument"))
    assert store.records(pid, "activities")[0]["status"] == "preparing"
    record_event(store, pid, run, SimpleNamespace(type="tool_result_start", tool_call_id="call1", tool_call_name="generate_media"))
    assert store.records(pid, "activities")[0]["status"] == "running"
    record_event(store, pid, run, SimpleNamespace(type="tool_result_end", tool_call_id="call1", state="error", metadata={"secret": "private-metadata"}))
    record = store.records(pid, "activities")[0]
    assert record["status"] == "failed"
    assert record["label"] == "提交媒体任务"
    assert "private" not in str(store.records(pid, "activities"))
    record_event(store, pid, run, SimpleNamespace(type="model_call_start", reply_id="model1"))
    close_activity(store, pid, run["id"], "interrupted")
    assert store.records(pid, "activities")[-1]["status"] == "interrupted"
    # Several model calls in the same agent reply have the same reply_id.
    for _ in range(2):
        record_event(store, pid, run, SimpleNamespace(type="model_call_start", reply_id="model1"))
        record_event(store, pid, run, SimpleNamespace(type="model_call_end", reply_id="model1"))
    assert len([a for a in store.records(pid, "activities") if a.get("category") == "model"]) == 3


def test_workspace_snapshot_exposes_safe_input_status_and_rename_survives_reload(tmp_path):
    app = create_app(tmp_path, enable_runtime=False)
    with TestClient(app, base_url="http://127.0.0.1:4318") as client:
        pid = client.post("/api/projects", json={}).json()["id"]
        app.state.store.put_record(pid, "inputs", {"source": "user", "status": "pending", "text": "private input"})
        assert client.put(f"/api/projects/{pid}/title", json={"title": "最后一班电梯"}).status_code == 200
        snapshot = client.get(f"/api/projects/{pid}").json()
        assert snapshot["project"]["title"] == "最后一班电梯"
        assert snapshot["inputs"][0]["status"] == "pending"
        assert "text" not in snapshot["inputs"][0]
        assert client.put(f"/api/projects/{pid}/title", json={"title": "  "}).status_code == 400
        for file in ("workspace.js", "panels.js", "workspace.css"):
            assert client.get('/' + file).status_code == 200


def test_streamed_reply_is_durable_and_replay_has_offsets(tmp_path):
    store = Store(tmp_path)
    pid = store.create_project()["id"]
    message = store.put_record(pid, "messages", {"role": "director", "text": "", "streaming": True})
    for delta in ("镜头 🎬", "继续拍摄"):
        store.append_message_text(pid, message["id"], delta)
    assert Store(tmp_path).record(message["id"])["text"] == "镜头 🎬继续拍摄"
    events = [e["body"] for e in store.events() if e["kind"] == "text_delta"]
    assert [e["offset"] for e in events] == [0, 4]
    assert "".join(e["delta"] for e in events) == store.record(message["id"])["text"]
