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

    def update_project(self, project_id, *, delivery=None, **changes):
        allowed = {"title", "mode", "status", "production_paused"}
        if set(changes) - allowed:
            raise ValueError("不可直接修改项目版本")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            p = self._project(con, project_id)
            p.update(changes)
            self._save_project(con, p)
            self._event(con, project_id, "project", p)
            if delivery:
                self._input(con, project_id, *delivery)
        return p

    def put_record(self, project_id, category, body, record_id=None):
        item = {**body, "id": record_id or uid(), "project_id": project_id, "created": now()}
        with self.connect() as con:
            self._project(con, project_id)
            con.execute("INSERT INTO records VALUES(?,?,?,?,?)",
                        (item["id"], project_id, category, json.dumps(item, ensure_ascii=False), item["created"]))
            self._event(con, project_id, category, item)
        return item

    def _input(self, con, project_id, input_id, text, source):
        item = {"id": input_id, "project_id": project_id, "created": now(),
                "text": text, "source": source, "status": "pending"}
        prior = con.execute("SELECT body,category FROM records WHERE id=?", (input_id,)).fetchone()
        if prior:
            if prior["category"] != "inputs" or json.loads(prior["body"])["text"] != text:
                raise Conflict("投递身份已用于不同输入")
            return json.loads(prior["body"])
        con.execute("INSERT INTO records VALUES(?,?,?,?,?)", (input_id, project_id, "inputs",
                    json.dumps(item, ensure_ascii=False), item["created"]))
        self._event(con, project_id, "inputs", item)
        return item

    def accept_message(self, project_id, message_id, text, annotation_ids):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self._project(con, project_id)
            prior = con.execute("SELECT * FROM records WHERE id=?", (message_id,)).fetchone()
            if prior:
                if prior["project_id"] != project_id or prior["category"] != "messages":
                    raise Conflict("此消息身份已被使用")
                message = json.loads(prior["body"])
                if message["text"] != text or message.get("annotation_ids", []) != annotation_ids:
                    raise Conflict("同一消息身份不能重复用于不同输入")
            else:
                message = {"id": message_id, "project_id": project_id, "created": now(),
                           "role": "user", "text": text, "annotation_ids": annotation_ids}
            annotations = [self._record(con, aid, project_id, "annotations") for aid in annotation_ids]
            for item in annotations:
                if item.get("removed") or item.get("submitted_message_id") not in {None, message_id}:
                    raise Conflict("标注已移除或已用于其他消息")
            input_text = text
            if annotations:
                # Stable source feedback, independent of later delivery bookkeeping.
                payload = [{k: a[k] for k in ["id", "artifact_id", "time", "text"]} for a in annotations]
                input_text += "\n本次一起提交的时间点标注：\n" + json.dumps(payload, ensure_ascii=False)
            self._input(con, project_id, "input-" + message_id, input_text, "user")
            if not prior:
                con.execute("INSERT INTO records VALUES(?,?,?,?,?)", (message_id, project_id, "messages",
                            json.dumps(message, ensure_ascii=False), message["created"]))
                self._event(con, project_id, "messages", message)
                for item in annotations:
                    item["submitted_message_id"] = message_id
                    con.execute("UPDATE records SET body=? WHERE id=?", (json.dumps(item, ensure_ascii=False), item["id"]))
                    self._event(con, project_id, "annotations", item)
        return message

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

    def update_record(self, record_id, *, delivery=None, **changes):
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
            if delivery:
                self._input(con, item["project_id"], *delivery)
        return item

    def create_artifact(self, project_id, kind, title, text="", meta=None, path=None):
        return self.put_record(project_id, "artifacts", {"kind": kind, "title": title,
            "text": text, "meta": meta or {}, "path": path})

    def _adopt(self, con, p, artifact, expected, *, restore_basis=False):
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
        if kind in {"film", "trial"} and restore_basis:
            for dependency, aid in artifact.get("meta", {}).get("basis", {}).items():
                if dependency in ({"proposal", "script", "visual_plan", "trial"} if kind == "film" else {"proposal", "script", "visual_plan"}):
                    self._record(con, aid, p["id"], "artifacts")
                    p["adopted"][dependency] = aid
            p["adopted"].pop("edit_plan", None)
        p["adopted"][kind] = artifact["id"]
        p["epoch"] += 1
        self._save_project(con, p)
        self._event(con, p["id"], "project", p)

    def adopt(self, project_id, artifact_id, expected, *, restore_basis=False, delivery=None):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            artifact = self._record(con, artifact_id, project_id, "artifacts")
            p = self._project(con, project_id)
            self._adopt(con, p, artifact, expected, restore_basis=restore_basis)
            if delivery:
                self._input(con, project_id, *delivery)
        return p

    def decide_review(self, project_id, review_id, approve, feedback="", authority="user", evidence_message_id=None):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            review = self._record(con, review_id, project_id, "reviews")
            if review["status"] != "pending":
                if (review["status"] == ("approved" if approve else "rejected") and review.get("feedback", "") == feedback
                        and review.get("authority") == authority):
                    return review
                raise Conflict("该审核已被处理")
            p = self._project(con, project_id)
            if approve:
                for kind, aid in review.get("dependencies", {}).items():
                    if p["adopted"].get(kind) != aid:
                        raise Conflict("审核所依据的版本已变化，请先由导演核对影响后重新提交；内容均已保留")
                artifact = self._record(con, review["artifact_id"], project_id, "artifacts")
                self._adopt(con, p, artifact, review["base"])
            review.update(status="approved" if approve else "rejected", feedback=feedback, authority=authority,
                          evidence_message_id=evidence_message_id)
            if authority == "user":
                text = f"用户{'批准' if approve else '未批准'}了 {review['kind']} 产物 {review['artifact_id']}。反馈：{feedback}"
                self._input(con, project_id, "review-" + review_id, text, "user_review")
            con.execute("UPDATE records SET body=? WHERE id=?", (json.dumps(review, ensure_ascii=False), review_id))
            self._event(con, project_id, "reviews", review)
        return review

    def save_draft(self, project_id, text, expected_revision, source_artifact_id=None):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            p = self._project(con, project_id)
            if p["draft"]["revision"] != expected_revision:
                raise Conflict("草稿已有新修改；当前编辑内容请保留后重试")
            if source_artifact_id:
                source = self._record(con, source_artifact_id, project_id, "artifacts")
                if source["kind"] != "script":
                    raise ValueError("草稿来源必须是剧本版本")
            if expected_revision == 0:
                p["draft"]["source_artifact_id"] = source_artifact_id or p["adopted"].get("script")
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
                    "meta": {"manual": True, "parent": draft.get("source_artifact_id"),
                             "adopted_at_submission": p["adopted"].get("script")}}
            con.execute("INSERT INTO records VALUES(?,?,?,?,?)", (item["id"], project_id, "artifacts",
                        json.dumps(item, ensure_ascii=False), item["created"]))
            draft.update(submitted_revision=expected_revision, submitted_id=item["id"])
            self._input(con, project_id, "draft-" + item["id"],
                f"用户明确提交了手改剧本 {item['id']}。请读取快照，先理解并提出修改意见和方案，按当前授权确认后再执行。", "user_edit")
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
