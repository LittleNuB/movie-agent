"""Persist a safe, user-visible execution trace, without model reasoning or arguments."""
from .store import now, uid

TOOL_LABELS = {
    "read_project": "读取项目状态", "read_artifact": "读取作品资料",
    "publish_document": "保存创作文稿", "generate_media": "提交媒体任务",
    "compose": "提交影片合成", "export_film_version": "提交版本导出",
    "inspect_media": "检查画面与连续性", "extract_frame": "提取参考画面",
    "recover_task": "核对已有媒体任务", "voice_catalog": "读取可用音色",
    "request_review": "准备作品审核", "record_user_review": "记录审核决定",
    "delegate": "委派专业任务", "resume_production": "恢复制作",
    "rename_project": "更新影片名称",
    "publish_production_brief": "保存剧本制作说明", "publish_reference_manifest": "整理参考资产",
    "compile_shot_input": "准备镜头生成输入", "submit_shot_input": "提交已规划镜头",
}


def record_event(store, project_id, run, event):
    kind = str(event.type).lower()
    if kind not in {"model_call_start", "model_call_end", "tool_call_start", "tool_result_start", "tool_result_end"}:
        return
    call_id = getattr(event, "tool_call_id", None)
    if call_id:
        key = run["id"] + "-tool-" + call_id
    elif kind == "model_call_start":
        # AgentScope reuses reply_id across several model calls in one reply.
        key = run["id"] + "-model-" + uid()
    else:
        active = next((a for a in reversed(store.records(project_id, "activities"))
                       if a["run_id"] == run["id"] and a.get("category") == "model"
                       and a["status"] == "running"), None)
        if not active:
            return
        key = active["id"]
    try:
        item = store.record(key, project_id, "activities")
    except KeyError:
        item = None
    if kind == "model_call_start":
        data = {"label": "请求模型", "status": "running", "category": "model"}
    elif kind == "model_call_end":
        data = {"status": "completed", "finished": now()}
    elif kind in {"tool_call_start", "tool_result_start"}:
        tool = event.tool_call_name
        data = {"tool": tool if tool in TOOL_LABELS else "project_tool",
                "label": TOOL_LABELS.get(tool, "执行项目工具"), "category": "tool",
                "status": "preparing" if kind == "tool_call_start" else "running"}
    else:
        state = str(event.state).lower()
        data = {"status": {"success": "completed", "interrupted": "interrupted", "denied": "denied"}.get(state, "failed"), "finished": now()}
    if item:
        store.update_record(key, **data)
    else:
        store.put_record(project_id, "activities", {"run_id": run["id"], "role": run["role"], **data}, key)


def close_activity(store, project_id, run_id, status):
    status = {"completed": "ended", "pending": "interrupted"}.get(status, status)
    for item in store.records(project_id, "activities"):
        if item["run_id"] == run_id and item.get("status") in {"preparing", "running"}:
            store.update_record(item["id"], status=status, finished=now())
