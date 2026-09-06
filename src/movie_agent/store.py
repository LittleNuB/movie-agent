"""Durable film records. SQLite transactions guard revisions and event ordering."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def uid():
    return uuid4().hex


def now():
    return datetime.now(UTC).isoformat()


class Conflict(ValueError):
    """The requested base is stale; no user data was overwritten."""


class Store:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / "films.sqlite3"
        with self.connect() as con:
            con.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, category TEXT NOT NULL,
                    body TEXT NOT NULL, created TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS records_project ON records(project_id,category,created);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
                    kind TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings (id TEXT PRIMARY KEY, body TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.db, timeout=15)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    @staticmethod
    def _project(con, project_id):
        row = con.execute("SELECT body FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise KeyError("影片不存在")
        return json.loads(row[0])

    @staticmethod
    def _save_project(con, p):
        p["updated"] = now()
        con.execute("UPDATE projects SET body=? WHERE id=?", (json.dumps(p, ensure_ascii=False), p["id"]))

    @staticmethod
    def _event(con, project_id, kind, data):
        con.execute("INSERT INTO events(project_id,kind,body,created) VALUES(?,?,?,?)",
                    (project_id, kind, json.dumps(data, ensure_ascii=False), now()))

    def create_project(self, title="新影片", mode="co"):
        if mode not in {"co", "auto", "audio"}:
            raise ValueError("未知创作模式")
        p = {"id": uid(), "title": title, "mode": mode, "epoch": 0, "adopted": {},
             "draft": {"text": "", "revision": 0, "submitted_revision": None},
             "status": "idle", "production_paused": False, "created": now(), "updated": now()}
        with self.connect() as con:
            con.execute("INSERT INTO projects VALUES(?,?)", (p["id"], json.dumps(p, ensure_ascii=False)))
            self._event(con, p["id"], "project", p)
        return p

    def project(self, project_id):
        with self.connect() as con:
            return self._project(con, project_id)

    def projects(self):
        with self.connect() as con:
            values = [json.loads(r[0]) for r in con.execute("SELECT body FROM projects")]
        return sorted(values, key=lambda p: p["updated"], reverse=True)

    def update_project(self, project_id, **changes):
        allowed = {"title", "mode", "status", "production_paused"}
        if set(changes) - allowed:
            raise ValueError("不可直接修改项目版本")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            p = self._project(con, project_id)
            p.update(changes)
            self._save_project(con, p)
            self._event(con, project_id, "project", p)
        return p

    def put_record(self, project_id, category, body, record_id=None):
        item = {**body, "id": record_id or uid(), "project_id": project_id, "created": now()}
        with self.connect() as con:
            self._project(con, project_id)
            con.execute("INSERT INTO records VALUES(?,?,?,?,?)",
                        (item["id"], project_id, category, json.dumps(item, ensure_ascii=False), item["created"]))
            self._event(con, project_id, category, item)
        return item

    def record(self, record_id, project_id=None, category=None):
        with self.connect() as con:
            return self._record(con, record_id, project_id, category)

    @staticmethod
    def _record(con, record_id, project_id=None, category=None):
        row = con.execute("SELECT project_id,body,category FROM records WHERE id=?", (record_id,)).fetchone()
        if not row or (project_id and row[0] != project_id) or (category and row[2] != category):
            raise KeyError("内容不存在或不属于当前影片")
        return json.loads(row[1])

    def records(self, project_id, category):
        with self.connect() as con:
            return [json.loads(r[0]) for r in con.execute(
                "SELECT body FROM records WHERE project_id=? AND category=? ORDER BY created,rowid",
                (project_id, category))]

    def update_record(self, record_id, **changes):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
            if not row:
                raise KeyError("内容不存在")
            if row["category"] == "artifacts":
                raise Conflict("产物版本不可覆盖")
            item = json.loads(row["body"])
            item.update({k: v for k, v in changes.items() if k not in {"id", "project_id", "created"}})
            con.execute("UPDATE records SET body=? WHERE id=?", (json.dumps(item, ensure_ascii=False), record_id))
            self._event(con, item["project_id"], row["category"], item)
        return item

    def create_artifact(self, project_id, kind, title, text="", meta=None, path=None):
        return self.put_record(project_id, "artifacts", {"kind": kind, "title": title,
            "text": text, "meta": meta or {}, "path": path})

    def _adopt(self, con, p, artifact, expected):
        kind = artifact["kind"]
        if p["adopted"].get(kind) != expected:
            raise Conflict("采用版本已变化，原版本与草稿均已保留，请刷新后重试")
        # Replacing an upstream decision never silently authorizes its old downstream work.
        dependencies = {"proposal": ["script", "visual_plan", "trial", "edit_plan"],
                        "script": ["visual_plan", "trial", "edit_plan"],
                        "visual_plan": ["trial"], "trial": [], "film": ["edit_plan"]}
        if expected != artifact["id"]:
            for dependent in dependencies.get(kind, []):
                p["adopted"].pop(dependent, None)
        if kind == "film":
            for dependency, aid in artifact.get("meta", {}).get("basis", {}).items():
                if dependency in {"proposal", "script", "visual_plan", "trial"}:
                    self._record(con, aid, p["id"], "artifacts")
                    p["adopted"][dependency] = aid
        p["adopted"][kind] = artifact["id"]
        p["epoch"] += 1
        self._save_project(con, p)
        self._event(con, p["id"], "project", p)

    def adopt(self, project_id, artifact_id, expected):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            artifact = self._record(con, artifact_id, project_id, "artifacts")
            p = self._project(con, project_id)
            self._adopt(con, p, artifact, expected)
        return p

    def decide_review(self, project_id, review_id, approve, feedback="", authority="user"):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            review = self._record(con, review_id, project_id, "reviews")
            if review["status"] != "pending":
                raise Conflict("该审核已被处理")
            p = self._project(con, project_id)
            if approve:
                for kind, aid in review.get("dependencies", {}).items():
                    if p["adopted"].get(kind) != aid:
                        raise Conflict("审核所依据的版本已变化，请先由导演核对影响后重新提交；内容均已保留")
                artifact = self._record(con, review["artifact_id"], project_id, "artifacts")
                self._adopt(con, p, artifact, review["base"])
            review.update(status="approved" if approve else "rejected", feedback=feedback, authority=authority)
            con.execute("UPDATE records SET body=? WHERE id=?", (json.dumps(review, ensure_ascii=False), review_id))
            self._event(con, project_id, "reviews", review)
        return review

    def save_draft(self, project_id, text, expected_revision):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            p = self._project(con, project_id)
            if p["draft"]["revision"] != expected_revision:
                raise Conflict("草稿已有新修改；当前编辑内容请保留后重试")
            p["draft"].update(text=text, revision=expected_revision + 1)
            self._save_project(con, p)
            self._event(con, project_id, "draft", p["draft"])
        return p["draft"]

    def submit_draft(self, project_id, expected_revision):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            p = self._project(con, project_id)
            draft = p["draft"]
            if draft["revision"] != expected_revision:
                raise Conflict("提交前草稿已变化，请保留当前内容并刷新")
            if draft.get("submitted_revision") == expected_revision:
                row = con.execute("SELECT body FROM records WHERE id=?", (draft["submitted_id"],)).fetchone()
                return json.loads(row[0])
            item = {"id": uid(), "project_id": project_id, "created": now(), "kind": "script",
                    "title": "手动修改的剧本", "text": draft["text"], "path": None,
                    "meta": {"manual": True, "parent": p["adopted"].get("script")}}
            con.execute("INSERT INTO records VALUES(?,?,?,?,?)", (item["id"], project_id, "artifacts",
                        json.dumps(item, ensure_ascii=False), item["created"]))
            draft.update(submitted_revision=expected_revision, submitted_id=item["id"])
            self._save_project(con, p)
            self._event(con, project_id, "artifacts", item)
            self._event(con, project_id, "draft", draft)
        return item

    def stop(self, project_id):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            p = self._project(con, project_id)
            p.update(status="stopped", production_paused=True, stopped_at=now(), epoch=p["epoch"] + 1)
            self._save_project(con, p)
            self._event(con, project_id, "project", p)
        return p

    def event(self, project_id, kind, data):
        with self.connect() as con:
            self._event(con, project_id, kind, data)

    def events(self, after=0, project_id=None):
        sql = "SELECT * FROM events WHERE seq>?"
        params = [after]
        if project_id:
            sql += " AND project_id=?"
            params.append(project_id)
        with self.connect() as con:
            return [{**dict(r), "body": json.loads(r["body"])} for r in con.execute(
                sql + " ORDER BY seq LIMIT 200", params)]

    def snapshot(self, project_id):
        return {"project": self.project(project_id), **{k: self.records(project_id, k)
                for k in ["messages", "artifacts", "reviews", "jobs", "annotations", "runs"]}}

    def setting(self, name, default=None):
        with self.connect() as con:
            row = con.execute("SELECT body FROM settings WHERE id=?", (name,)).fetchone()
        return json.loads(row[0]) if row else default

    def save_setting(self, name, value):
        with self.connect() as con:
            con.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                        (name, json.dumps(value, ensure_ascii=False)))

    def media_path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root / "media"):
            raise ValueError("非法素材路径")
        return path
