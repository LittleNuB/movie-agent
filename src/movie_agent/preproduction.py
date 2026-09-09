"""Versioned production knowledge and concrete shot inputs (ADR 0007).

Original application code informed by the research recorded in docs/research/.
Structural checks are not story scores, visual judgments, or creative approval.
"""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .providers import Provider
from .store import Conflict

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Entity(Record):
    id: Identifier
    kind: Literal["character", "scene", "prop"]
    name: Text
    description: Text
    origin: Literal["script", "creative_addition"]


class StoryEvent(Record):
    id: Identifier
    entity_ids: list[Identifier]
    motivation: Text
    preconditions: Text
    action: Text
    result: Text
    state_before: Text
    state_after: Text
    audience_information: Text
    screen_expression: Text
    source_location: Text
    depends_on: list[Identifier] = Field(default_factory=list)


class ProductionBrief(Record):
    script_id: Identifier
    entities: list[Entity]
    events: list[StoryEvent] = Field(min_length=1)
    world_rules: list[Text] = Field(default_factory=list)
    open_questions: list[Text] = Field(default_factory=list)


class ReferenceEntry(Record):
    id: Identifier
    artifact_id: Identifier
    entity_ids: list[Identifier] = Field(min_length=1)
    purpose: Text
    story_state: Text
    view: Text
    status: Literal["candidate", "standard", "supplement", "rejected"] = "candidate"
    parent_asset_ids: list[Identifier] = Field(default_factory=list)
    evidence_ids: list[Identifier] = Field(default_factory=list)
    assessment: Text


class ReferenceManifest(Record):
    brief_id: Identifier
    entries: list[ReferenceEntry] = Field(min_length=1)


class ShotReference(Record):
    entry_id: Identifier
    role: Literal["first_frame", "last_frame", "reference_image", "reference_video", "reference_audio"]
    controls: Text


class ShotSpec(Record):
    brief_id: Identifier
    manifest_id: Identifier | None = None
    unit_id: Identifier
    event_ids: list[Identifier] = Field(min_length=1)
    entity_ids: list[Identifier]
    intent: Text
    story_state: Text
    start_frame: Text
    end_frame: Text
    action: Text
    camera: Text
    sound: Text
    path: Literal["text", "frames", "multimodal"]
    path_reason: Text
    references: list[ShotReference] = Field(default_factory=list)
    no_reference_reason: str = ""


class AnimaticBoard(Record):
    artifact_id: Identifier
    event_ids: list[Identifier] = Field(min_length=1)
    duration: float = Field(ge=1 / 24, allow_inf_nan=False)


class AnimaticTrack(Record):
    artifact_id: Identifier
    start: float = Field(default=0, ge=0, allow_inf_nan=False)
    source_start: float = Field(default=0, ge=0, allow_inf_nan=False)
    duration: float | None = Field(default=None, ge=0.04, allow_inf_nan=False)
    gain: float = Field(default=1, gt=0, allow_inf_nan=False)


def unique(values, label):
    if len(values) != len(set(values)):
        raise ValueError(f"{label}不能重复")


def subset(values, known, label):
    if set(values) - set(known):
        raise ValueError(f"{label}引用了不存在的身份：" + "、".join(sorted(set(values) - set(known))))


def binding_identity(binding):
    # No credentials, including in persisted framework tool output.
    return {key: getattr(binding, key) for key in ("connection_id", "protocol", "base_url", "model")}


class Preproduction:
    def __init__(self, store):
        self.store = store

    def artifact(self, project_id, artifact_id, kind=None):
        item = self.store.record(artifact_id, project_id, "artifacts")
        if kind and item["kind"] != kind:
            raise ValueError(f"需要 {kind} 类型的具体产物版本")
        return item

    def media(self, project_id, artifact_id):
        item = self.artifact(project_id, artifact_id)
        if item["kind"] not in {"image", "video", "audio"} or not item.get("path"):
            raise ValueError("参考需要实际图片、视频或声音")
        if not self.store.media_path(item["path"]).is_file():
            raise ValueError("参考文件尚不存在，请先生成或取回已有结果")
        return item

    def current(self, project_id, item):
        adopted = self.store.project(project_id)["adopted"]
        basis = item.get("meta", {}).get("basis", {})
        if not basis.get("script") or any(adopted.get(k) != v for k, v in basis.items()):
            raise Conflict("制作依据已过时或剧本未采用，请保留旧版本并基于当前决定核对")
        if item.get("meta", {}).get("candidate_only"):
            raise Conflict("迟到制作说明仅为候选，需要按当前依据重新发布")

    def animatic_plan(self, project_id, brief_id, boards, tracks):
        brief = self.artifact(project_id, brief_id, "production_brief")
        self.current(project_id, brief)
        if not boards or not tracks:
            raise ValueError("有声分镜预演需要实际图片和至少一份临时声音；只有静帧不能称为有声预演")
        boards = [AnimaticBoard.model_validate(b) for b in boards]
        tracks = [AnimaticTrack.model_validate(t) for t in tracks]
        known_events = [e["id"] for e in brief["meta"]["brief"]["events"]]
        for board in boards:
            subset(board.event_ids, known_events, "预演事件")
            if self.media(project_id, board.artifact_id)["kind"] != "image":
                raise ValueError("分镜预演画面需要静态图片，真实视频请用试拍合成")
        for track in tracks:
            if self.media(project_id, track.artifact_id)["kind"] != "audio":
                raise ValueError("预演临时声音需要实际音频产物")
        # Quantize cumulative boundaries, not each segment independently: many
        # fractional boards must not accumulate a full-frame rounding error each.
        clips, requested_end, prior_frames = [], 0, 0
        for board in boards:
            requested_end += board.duration
            end_frames = max(prior_frames + 1, math.floor(requested_end * 24 + 0.5))
            clips.append({"artifact_id": board.artifact_id, "duration": (end_frames - prior_frames) / 24, "audio_gain": 0})
            prior_frames = end_frames
        if any(t.start >= prior_frames / 24 for t in tracks):
            raise ValueError("临时声音开始位置超出预演时长")
        return {"kind": "animatic", "stage": "animatic", "basis_id": brief_id, "brief_id": brief_id,
                "boards": [b.model_dump() for b in boards],
                "clips": clips,
                "tracks": [t.model_dump(exclude_none=True) for t in tracks]}

    def validate_animatic(self, project_id, purpose, args):
        if args.get("stage") == "animatic" or args.get("kind") == "animatic":
            if purpose != "compose" or args.get("kind") != "animatic" or args.get("stage") != "animatic":
                raise ValueError("预演不能伪装为真实试拍、影片或外部生成任务")
            expected = self.animatic_plan(project_id, args.get("brief_id"), args.get("boards"), args.get("tracks"))
            if args != expected:
                raise ValueError("预演合成输入与实际分镜、声音或制作依据不一致")

    def save(self, project_id, kind, title, text, data, script_id, author, parent_id=None, basis=None):
        if not title.strip():
            raise ValueError("制作文稿需要标题")
        if parent_id:
            self.artifact(project_id, parent_id, kind)
        self.artifact(project_id, script_id, "script")
        basis = basis or {"script": script_id}
        adopted = self.store.project(project_id)["adopted"]
        return self.store.create_artifact(project_id, kind, title, text, {
            **data, "schema_version": 1, "basis": basis, "author": author, "parent": parent_id,
            "candidate_only": any(adopted.get(k) != v for k, v in basis.items()),
        })

    def publish_brief(self, project_id, title, brief: ProductionBrief, author, parent_id=None):
        entities = [entity.id for entity in brief.entities]
        events = [event.id for event in brief.events]
        unique(entities, "实体身份")
        unique(events, "事件身份")
        for event in brief.events:
            subset(event.entity_ids, entities, "事件实体")
            subset(event.depends_on, events, "事件依赖")
        # Deliberately no narrative-order or causal-cycle rule: nonlinear stories are valid.
        lines = ["结构检查仅核对数据和引用，不代表故事质量通过。", "\n## 人物、场景与道具"]
        for entity in brief.entities:
            origin = "剧本已有" if entity.origin == "script" else "创作补充"
            lines += [f"- **{entity.name}**（{entity.id}，{origin}）：{entity.description}"]
        lines += ["\n## 世界规则", *[f"- {rule}" for rule in brief.world_rules], "\n## 关键事件"]
        for event in brief.events:
            lines += [f"\n### {event.id} · {event.source_location}",
                      f"- 人物动机／发生原因：{event.motivation}", f"- 必要前提：{event.preconditions}",
                      f"- 行动：{event.action}", f"- 结果：{event.result}",
                      f"- 开始状态：{event.state_before}", f"- 结束状态：{event.state_after}",
                      f"- 观众获得的信息：{event.audience_information}",
                      f"- 画面与声音如何表达：{event.screen_expression}",
                      f"- 相关实体：{'、'.join(event.entity_ids) or '无'}；前提事件：{'、'.join(event.depends_on) or '无'}"]
        lines += ["\n## 尚需创作判断的问题", *[f"- {q}" for q in brief.open_questions]]
        return self.save(project_id, "production_brief", title, "\n".join(lines),
                         {"brief": brief.model_dump()}, brief.script_id, author, parent_id)

    def publish_manifest(self, project_id, title, manifest: ReferenceManifest, author, parent_id=None):
        brief_item = self.artifact(project_id, manifest.brief_id, "production_brief")
        brief = ProductionBrief.model_validate(brief_item["meta"]["brief"])
        unique([entry.id for entry in manifest.entries], "参考条目身份")
        lines = ["标准／补充状态记录专业判断与依据，不代表用户批准或自动质量验收。"]
        provenance = {}
        for entry in manifest.entries:
            subset(entry.entity_ids, [e.id for e in brief.entities], "参考实体")
            asset = self.media(project_id, entry.artifact_id)
            meta = asset.get("meta", {})
            actual_parents = {ref["artifact_id"] for ref in meta.get("references", [])}
            if meta.get("source_artifact_id"):
                actual_parents.add(meta["source_artifact_id"])
            if set(entry.parent_asset_ids) - actual_parents:
                raise ValueError("派生来源必须出现在素材实际生成参考或抽帧记录中，不能补造引用")
            for aid in entry.parent_asset_ids:
                self.media(project_id, aid)
            evidence_targets = set()
            for eid in entry.evidence_ids:
                evidence = self.artifact(project_id, eid, "continuity_check")
                run_id = evidence.get("meta", {}).get("run_id")
                if not run_id:
                    raise ValueError("参考检查依据需要实际 inspect_media 观察记录，普通文稿不能冒充已查看媒体")
                run = self.store.record(run_id, project_id, "runs")
                if (run.get("role") != "visual_evidence" or run.get("status") != "completed"
                        or run.get("artifact_id") != eid):
                    raise ValueError("媒体观察未完成或没有与检查结果对应")
                evidence_targets.update(e["artifact_id"] for e in run.get("evidence", []))
            if entry.status in {"standard", "supplement"} and entry.artifact_id not in evidence_targets:
                raise ValueError("标准或补充参考需要包含该素材实际观察位置的检查记录；没有依据时保存为候选")
            provenance[entry.id] = {"job_id": meta.get("job_id"),
                                    "actual_parent_asset_ids": sorted(actual_parents),
                                    "source_time": meta.get("source_time")}
            labels = {"candidate": "候选", "standard": "标准", "supplement": "补充", "rejected": "不适用"}
            lines += [f"\n## {entry.id} · {asset['title']}（{labels[entry.status]}）",
                      f"- 对应实体：{'、'.join(entry.entity_ids)}", f"- 用途：{entry.purpose}",
                      f"- 剧情状态：{entry.story_state}", f"- 视角：{entry.view}",
                      f"- 判断依据：{entry.assessment}", f"- 素材版本：{entry.artifact_id}",
                      f"- 派生来源：{'、'.join(entry.parent_asset_ids) or '无登记派生'}",
                      f"- 检查记录：{'、'.join(entry.evidence_ids) or '尚无'}"]
        return self.save(project_id, "reference_manifest", title, "\n".join(lines),
                         {"manifest": manifest.model_dump(), "brief_id": manifest.brief_id, "provenance": provenance,
                          "asset_ids": list(dict.fromkeys(e.artifact_id for e in manifest.entries))},
                         brief.script_id, author, parent_id)

    def shot_materials(self, project_id, spec: ShotSpec):
        brief_item = self.artifact(project_id, spec.brief_id, "production_brief")
        self.current(project_id, brief_item)
        brief = ProductionBrief.model_validate(brief_item["meta"]["brief"])
        subset(spec.event_ids, [event.id for event in brief.events], "镜头事件")
        subset(spec.entity_ids, [entity.id for entity in brief.entities], "镜头实体")
        references, details = [], []
        manifest_entries = {}
        if spec.manifest_id:
            manifest_item = self.artifact(project_id, spec.manifest_id, "reference_manifest")
            self.current(project_id, manifest_item)
            manifest = ReferenceManifest.model_validate(manifest_item["meta"]["manifest"])
            if manifest.brief_id != spec.brief_id:
                raise ValueError("镜头与参考清单需要引用同一制作说明版本")
            manifest_entries = {entry.id: entry for entry in manifest.entries}
        for ref in spec.references:
            if ref.entry_id not in manifest_entries:
                raise ValueError("镜头参考未在指定清单中登记")
            entry = manifest_entries[ref.entry_id]
            if entry.status not in {"standard", "supplement"}:
                raise ValueError("镜头使用的参考需先检查并登记为标准或补充，候选和不适用项仍保留")
            subset(entry.entity_ids, spec.entity_ids, "参考覆盖的镜头实体")
            asset = self.media(project_id, entry.artifact_id)
            expected = {"reference_audio": "audio", "reference_video": "video"}.get(ref.role, "image")
            if asset["kind"] != expected:
                raise ValueError("镜头参考角色与真实素材类型不一致")
            references.append({"artifact_id": entry.artifact_id, "role": ref.role})
            details.append({"entry_id": entry.id, "entity_ids": entry.entity_ids, "view": entry.view,
                            "story_state": entry.story_state, "controls": ref.controls,
                            "purpose": entry.purpose, "assessment": entry.assessment})
        unique([(ref["artifact_id"], ref["role"]) for ref in references], "镜头参考")
        roles = [ref["role"] for ref in references]
        if spec.path == "text" and references:
            raise ValueError("文生路径不能悄悄附加参考，请明确改变路径")
        if spec.path == "frames" and (not roles or set(roles) - {"first_frame", "last_frame"}):
            raise ValueError("帧路径需要首帧或尾帧，不能混用其他参考")
        if spec.path == "frames" and len(roles) != len(set(roles)):
            raise ValueError("首帧与尾帧各只能有一份")
        if spec.path == "multimodal" and (not roles or set(roles) & {"first_frame", "last_frame"}):
            raise ValueError(
                "多模态路径需要参考素材，不能混入首尾帧角色。"
                "若要首帧／尾帧约束，请使用 path=frames 并保留 first_frame／last_frame 角色；"
                "reference_image 仅为普通参考，不能为了通过校验而改变已承诺的生成路径。"
            )
        if spec.entity_ids and not references and not spec.no_reference_reason.strip():
            raise ValueError("涉及已登记实体但未使用参考，请说明当前镜头的选择理由")
        return brief, references, details

    def compile(self, project_id, title, spec: ShotSpec, purpose, binding, parameters, client, author):
        if binding.protocol not in {"minimax_video", "ark"}:
            raise ValueError("当前镜头编译尚未支持此视频协议")
        brief, references, details = self.shot_materials(project_id, spec)
        Provider(binding, client).validate(purpose, parameters, references)
        entities = {entity.id: entity for entity in brief.entities}
        prompt_lines = [f"镜头任务：{spec.intent}", f"剧情状态：{spec.story_state}",
                        *[f"主体 {eid}（{entities[eid].name}）：{entities[eid].description}" for eid in spec.entity_ids],
                        f"开始构图：{spec.start_frame}", f"结束状态：{spec.end_frame}",
                        f"画内动作：{spec.action}", f"摄影机：{spec.camera}", f"声音：{spec.sound}"]
        counts = {}
        for ref, detail in zip(references, details):
            media_type = {"reference_audio": "音频", "reference_video": "视频"}.get(ref["role"], "图片")
            counts[media_type] = counts.get(media_type, 0) + 1
            label = ("首帧" if ref["role"] == "first_frame" else "尾帧" if ref["role"] == "last_frame"
                     else f"{media_type}{counts[media_type]}")
            prompt_lines.append(f"{label}用途：{detail['controls']}；参考状态：{detail['story_state']}；视角：{detail['view']}")
        warnings = []
        if binding.protocol == "ark" and references:
            warnings.append("人物参考优先面部与全身，避免默认多视图拼版；实际肖像来源是否受信仍由服务核验。")
        if spec.path == "multimodal":
            warnings.append("多模态提示中的起止构图是目标描述，不等于首尾帧硬约束。")
        prompt = "\n".join(prompt_lines)
        path_label = {"text": "纯文本", "frames": "首尾帧", "multimodal": "多模态参考（不是首帧锁定）"}[spec.path]
        basis = {k: v for k, v in self.store.project(project_id)["adopted"].items() if k in {"script", "visual_plan"}}
        basis["script"] = brief.script_id
        data = {"spec": spec.model_dump(), "brief_id": spec.brief_id, "manifest_id": spec.manifest_id,
                "binding": binding_identity(binding), "purpose": purpose, "parameters": parameters,
                "references": references, "reference_details": details, "prompt": prompt,
                "warnings": warnings, "unit_id": spec.unit_id, "asset_ids": [r["artifact_id"] for r in references]}
        text = ("请求已编译，尚未提交生成；字段完整不代表声画通过。\n\n"
                f"- 镜头：{spec.unit_id}\n- 相关事件：{'、'.join(spec.event_ids)}\n"
                f"- 实际输入模式：{path_label}\n"
                f"- 实际参考角色：{'、'.join(r['artifact_id'] + ' (' + r['role'] + ')' for r in references) or '无'}\n"
                f"- 路径选择：{spec.path_reason}\n- 不用参考的理由：{spec.no_reference_reason or '已使用参考'}\n"
                f"- 模型：{binding.model}\n- 时长：{parameters.get('duration', 10)}秒\n"
                f"- 制作说明：{spec.brief_id}\n- 参考清单：{spec.manifest_id or '无'}\n\n"
                "## 实际生成提示\n\n" + prompt + "\n\n## 适用说明\n" + "\n".join(warnings))
        return self.save(project_id, "shot_input", title, text, data, brief.script_id, author, basis=basis)

    def verify_submission(self, project_id, input_id, args, purpose, binding=None):
        item = self.artifact(project_id, input_id, "shot_input")
        self.current(project_id, item)
        meta = item["meta"]
        _, references, _ = self.shot_materials(project_id, ShotSpec.model_validate(meta["spec"]))
        if purpose != meta["purpose"] or (binding and binding_identity(binding) != meta["binding"]):
            raise Conflict("模型用途或连接已改变，请保留旧镜头输入并重新编译")
        expected = {"prompt": meta["prompt"], "parameters": meta["parameters"], "references": references,
                    "unit_id": meta["unit_id"], "expected_model": meta["binding"]["model"]}
        if any(args.get(key) != value for key, value in expected.items()):
            raise Conflict("提交内容与已编译镜头不一致，请形成新的镜头输入版本")
        return item

    def bind_input(self, project_id, args):
        """A compiled basis implies its input identity even on the generic media tool.

        Legacy job arguments retain their existing gate behavior. An explicit or
        inferred compiled identity always goes through verify_submission.
        """
        input_id = args.get("shot_input_id")
        try:
            basis = self.artifact(project_id, args.get("basis_id"))
        except KeyError:
            basis = None
        if basis and basis["kind"] == "shot_input":
            if input_id and input_id != basis["id"]:
                raise Conflict("编译镜头身份与制作依据不一致")
            input_id = basis["id"]
        return {**args, "shot_input_id": input_id} if input_id else args
