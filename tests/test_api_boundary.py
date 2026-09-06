from fastapi.testclient import TestClient

from movie_agent.api import create_app


class MemoryVault:
    def __init__(self):
        self.keys = {}

    def get(self, name):
        return self.keys.get(name)

    def set(self, name, key):
        self.keys[name] = key

    def delete(self, name):
        self.keys.pop(name, None)


def test_secret_and_local_origin_boundaries(tmp_path):
    app = create_app(tmp_path, vault=MemoryVault(), enable_runtime=False)
    with TestClient(app, base_url="http://127.0.0.1:4318") as client:
        assert client.get("/api/config").json()["connections"] == []
        body = {"id": "test", "name": "Local test", "protocol": "openai", "base_url": "https://example.com/v1",
                "api_key": "test-private-secret"}
        saved = client.put("/api/connections", json=body)
        assert saved.status_code == 200
        assert "test-private-secret" not in saved.text
        assert "test-private-secret" not in client.get("/api/config").text
        assert b"test-private-secret" not in app.state.store.db.read_bytes()
        body["models"] = [{"id": "test", "capability": "text", "parameters": {"api_key": "test-private-secret"}}]
        rejected = client.put("/api/connections", json=body)
        assert rejected.status_code == 422
        assert "test-private-secret" not in rejected.text
        assert client.post("/api/projects", json={}, headers={"origin": "https://foreign.example"}).status_code == 403
        assert client.post("/api/projects", content="{}", headers={"content-type": "text/plain"}).status_code == 415
        assert client.get("/api/projects", headers={"host": "foreign.example"}).status_code == 403


def test_messages_are_idempotent_and_annotations_keep_source_time(tmp_path):
    app = create_app(tmp_path, vault=MemoryVault(), enable_runtime=False)
    with TestClient(app, base_url="http://127.0.0.1:4318") as client:
        pid = client.post("/api/projects", json={}).json()["id"]
        video = app.state.store.create_artifact(pid, "trial", "fixture", meta={"media": {"duration": 5}})
        aid = client.post(f"/api/projects/{pid}/annotations", json={"artifact_id": video["id"], "time": 2, "text": "Quieter"}).json()["id"]
        assert client.put(f"/api/projects/{pid}/annotations/{aid}", json={"artifact_id": video["id"], "time": 50, "text": "Quieter"}).status_code == 400
        msg = {"text": "Discuss these changes first", "client_id": "same-message", "annotation_ids": [aid]}
        first = client.post(f"/api/projects/{pid}/messages", json=msg)
        repeat = client.post(f"/api/projects/{pid}/messages", json=msg)
        assert first.status_code == repeat.status_code == 200
        snapshot = client.get(f"/api/projects/{pid}").json()
        assert len(snapshot["messages"]) == 1
        assert snapshot["jobs"] == []
        assert len(app.state.store.records(pid, "inputs")) == 1
        assert client.post(f"/api/projects/{pid}/messages", json={**msg, "text": "Changed"}).status_code == 409
