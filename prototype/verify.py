"""Focused browser acceptance for the throwaway prototype (requires Python Playwright)."""
import json
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("PROTOTYPE_URL", "http://127.0.0.1:4317")
OUT = Path(".cache/prototype")
OUT.mkdir(parents=True, exist_ok=True)
checks, errors, external = [], [], []


def passed(name):
    checks.append(name)
    print("PASS", name, flush=True)


def snapshot(page, name):
    page.wait_for_timeout(280)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)


def state(page):
    return page.evaluate("JSON.parse(localStorage.getItem('movie-agent.prototype.v1'))")


def project(page):
    s = state(page)
    return next(p for p in s["projects"] if p["id"] == s["activeId"])


def send(page, text):
    page.get_by_role("textbox", name="给导演的消息").fill(text)
    page.get_by_role("button", name="发送消息", exact=True).click()


def action(page, name, **kwargs):
    page.locator(f'[data-action="{name}"]').first.click(**kwargs)


def annotate(page, seconds, text):
    page.locator("#seek").fill(str(seconds))
    page.get_by_role("button", name="添加标注", exact=True).click()
    page.get_by_role("textbox", name="此处的修改意见").fill(text)
    page.locator('[data-action="annotation-add"]').click()


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light")
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("request", lambda req: external.append(req.url) if not req.url.startswith(BASE) else None)
    page.goto(BASE, wait_until="networkidle")
    expect(page.get_by_role("heading", name="你想拍一个怎样的故事？")).to_be_visible()
    assert state(page)["activeId"] is None
    snapshot(page, "welcome")
    action(page, "example")
    assert state(page)["activeId"] is None
    expect(page.get_by_role("textbox", name="给导演的消息")).not_to_be_empty()
    passed("welcome example fills without sending or creating a project")

    action(page, "settings")
    assert page.locator("#demo-director").get_attribute("readonly") is not None
    page.locator('[data-action="demo-key"][data-id="director"]').click()
    page.locator('[data-action="check-key"][data-id="director"]').click()
    expect(page.locator("#check-director")).to_contain_text("模拟连接成功")
    page.locator("#simulate-key-failure").check()
    page.locator('[data-action="check-key"][data-id="director"]').click()
    expect(page.locator("#check-director")).to_contain_text("模拟失败")
    snapshot(page, "settings")
    action(page, "settings-done")
    assert "DEMO-ONLY-NOT-A-KEY" not in json.dumps(state(page))
    passed("settings shows simulated success and failure without saving credentials")

    action(page, "demo")
    p = project(page)
    original_id = p["id"]
    original_video = p["adoptedId"]
    original_versions = len(p["versions"])
    snapshot(page, "workspace-day")
    action(page, "play")
    page.wait_for_timeout(1150)
    action(page, "play")
    assert project(page)["playheads"][original_video] > 42
    annotate(page, 42, "音乐再轻一些")
    count_before = len(project(page)["messages"])
    annotate(page, 63, "环境声可以再保留久一点")
    assert len(project(page)["messages"]) == count_before
    assert len(project(page)["annotations"]) == 2
    page.locator('[data-annotation-input]').first.fill("音乐延后进入")
    snapshot(page, "annotations-day")
    page.locator('[data-action="annotation-send"]').first.click()
    assert len(project(page)["annotations"]) == 1
    assert project(page)["pending"]["scope"] == "audio"
    assert project(page)["task"] is None
    send(page, "整体保持安静")
    assert len(project(page)["annotations"]) == 0
    assert project(page)["messages"][-2]["annotations"][0]["versionId"] == original_video
    passed("playback, seek, annotation drafts, editing, individual and combined send")

    action(page, "mode")
    page.locator('[name="mode"][value="audio"]').check()
    action(page, "mode-save")
    # The mixed overall feedback remains subject to co-creation review.
    send(page, "音乐再轻一点")
    assert project(page)["task"] is not None
    assert project(page)["mode"] == "audio"
    send(page, "现在进度怎么样")
    assert project(page)["task"] is not None
    action(page, "stop")
    assert project(page)["task"]["status"] == "stopping"
    page.wait_for_timeout(1700)
    assert project(page)["task"] is None
    assert project(page)["stage"] == "stopped"
    assert len(project(page)["versions"]) == original_versions
    passed("partial audio delegation, messaging during work, stop request then completion")

    send(page, "切换到共创")
    assert project(page)["mode"] == "co"
    # User saves, submits one snapshot, then edits again before approving the first.
    page.get_by_role("tab", name="剧本", exact=True).click()
    editor = page.get_by_role("textbox", name="剧本编辑器")
    baseline = editor.input_value()
    submitted = baseline + "\n\n提交稿：把最后一句改成‘我在这里。’"
    later = submitted + "\n后续手改：这句还没有提交。"
    editor.fill(submitted)
    assert project(page)["task"] is None
    assert project(page)["appliedScript"] == baseline
    action(page, "script-submit")
    review_id = project(page)["pending"]["id"]
    editor.fill(later)
    snapshot(page, "script-draft")
    page.locator(f'[data-action="review-view"][data-id="{review_id}"]').click()
    expect(page.locator("dialog pre")).to_have_text(submitted)
    page.locator(f'dialog [data-action="approve"][data-id="{review_id}"]').click()
    # Script save during rendering cannot be destroyed by a task callback.
    page.wait_for_timeout(12500)
    assert project(page)["appliedScript"] == submitted
    assert project(page)["draftScript"] == later
    assert len(project(page)["versions"]) == original_versions + 1
    expect(editor).to_have_value(later)
    page.locator('[data-action="asset"][data-kind="video"]').first.click()
    assert project(page)["activeTab"] == "video:" + original_video
    assert project(page)["adoptedId"] != original_video
    passed("historical message artifact remains bound to its original version")
    passed("save differs from submit; review binds snapshot; later draft survives completion")

    action(page, "library")
    latest = project(page)["adoptedId"]
    page.locator(f'[data-action="library-open"][data-id="{latest}"]').click()
    action(page, "history")
    old = project(page)["versions"][0]["id"]
    page.locator(f'[data-action="library-open"][data-id="{old}"]').click()
    assert project(page)["adoptedId"] == latest
    annotate(page, 10, "旧版这里先留白")
    assert project(page)["annotations"][0]["versionId"] == old
    action(page, "version-continue")
    assert project(page)["adoptedId"] == old
    assert any(b["text"] == later for b in project(page)["draftBackups"])
    assert len(project(page)["versions"]) == original_versions + 1
    page.get_by_role("tab", name="剧本", exact=True).click()
    action(page, "backups")
    page.locator('[data-action="library-open"][data-kind="backup"]').first.click()
    action(page, "backup-restore")
    assert project(page)["draftScript"] == later
    assert project(page)["appliedScript"] != later
    passed("history viewing does not adopt; explicit continuation preserves and restores draft")

    action(page, "work-close")
    send(page, "声音里保留呼吸")
    assert project(page)["workOpen"] is False
    send(page, "确认")
    send(page, "进度如何")
    action(page, "stop")
    page.wait_for_timeout(1700)
    assert project(page)["workOpen"] is False
    action(page, "work-open")
    action(page, "nav")
    assert page.locator(".shell").evaluate("e => e.classList.contains('nav-closed')")
    action(page, "nav")
    passed("collapsed panels remain collapsed during new feedback and task transitions")

    action(page, "demo-menu")
    action(page, "simulate-failure")
    assert project(page)["stage"] == "failed"
    assert project(page)["messages"][-1]["role"] == "director"
    send(page, "继续")
    assert project(page)["task"] is not None
    other = next(p["id"] for p in state(page)["projects"] if p["id"] != original_id)
    page.locator(f'[data-action="project"][data-id="{other}"]').click()
    expect(page.get_by_role("textbox", name="给导演的消息")).to_have_value("我想要一种温柔的不安。")
    page.wait_for_timeout(12500)
    page.locator(f'[data-action="project"][data-id="{original_id}"]').click()
    assert project(page)["stage"] in ["trial", "finished"]
    assert project(page)["task"] is None
    assert project(page)["draftScript"] == later
    passed("ordinary-text failure recovery and project switching during a sample task")

    action(page, "theme")
    page.locator('[name="theme"][value="dark"]').check()
    action(page, "theme-save")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    action(page, "library")
    latest = project(page)["adoptedId"]
    page.locator(f'[data-action="library-open"][data-id="{latest}"]').click()
    snapshot(page, "workspace-night")
    for width, height in [(1280, 800), (1920, 1080)]:
        page.set_viewport_size({"width": width, "height": height})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        expect(page.get_by_role("textbox", name="给导演的消息")).to_be_visible()
        expect(page.get_by_role("button", name="添加标注", exact=True)).to_be_visible()
        snapshot(page, f"night-{width}")
    action(page, "history")
    page.locator(f'[data-action="library-open"][data-id="{old}"]').click()
    annotate(page, 17, "保留到刷新后的标注")
    action(page, "history")
    page.locator(f'[data-action="library-open"][data-id="{latest}"]').click()
    page.reload(wait_until="networkidle")
    assert project(page)["id"] == original_id
    assert project(page)["draftScript"] == later
    assert project(page)["annotations"][0]["versionId"] == old
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    passed("day/night, desktop widths, reload retains theme, project, drafts and annotation provenance")

    send(page, "音乐再轻一点")
    send(page, "同意")
    assert project(page)["task"] is not None
    page.reload(wait_until="networkidle")
    assert project(page)["task"] is None
    assert project(page)["stage"] == "stopped"
    assert "真实后台" in project(page)["messages"][-1]["text"]
    passed("reload does not claim sample work continued with the page closed")

    # Fresh full-delegation path, with actual timed DOM transitions through completion.
    action(page, "new")
    action(page, "mode")
    page.locator('[name="mode"][value="auto"]').check()
    action(page, "mode-save")
    send(page, "一个人在轨道站等女儿的回信")
    new_id = project(page)["id"]
    assert project(page)["mode"] == "auto"
    assert project(page)["workOpen"] is True
    assert project(page)["activeTab"].startswith("proposal:")
    assert project(page)["task"] is not None
    deadline = time.time() + 30
    while project(page)["stage"] != "finished" and time.time() < deadline:
        page.wait_for_timeout(700)
    assert project(page)["stage"] == "finished"
    assert len(project(page)["versions"]) == 2
    assert project(page)["pending"] is None
    assert project(page)["activeTab"].startswith("proposal:")
    passed("first send creates project; full delegation completes while preserving viewed artifact")

    action(page, "new")
    action(page, "mode")
    page.locator('[name="mode"][value="co"]').check()
    action(page, "mode-save")
    send(page, "一个安静的科幻故事")
    send(page, "结尾能更温柔一点吗")
    assert project(page)["pending"]["kind"] == "proposal"
    send(page, "同意")
    assert project(page)["pending"]["kind"] == "script"
    assert project(page)["versions"] == []
    send(page, "这里的动作再克制一点")
    assert project(page)["pending"]["kind"] == "script"
    send(page, "同意")
    page.wait_for_timeout(5900)
    assert project(page)["pending"]["kind"] == "visual"
    assert project(page)["versions"] == []
    send(page, "我希望光线更柔和")
    assert project(page)["pending"]["kind"] == "visual"
    send(page, "同意")
    page.wait_for_timeout(5900)
    assert project(page)["pending"]["kind"] == "trial"
    send(page, "这里音乐再轻一点")
    assert project(page)["pending"]["kind"] == "revision"
    send(page, "同意")
    action(page, "stop")
    page.wait_for_timeout(1700)
    send(page, "继续")
    page.wait_for_timeout(12500)
    assert project(page)["pending"]["kind"] == "trial"
    assert project(page)["stage"] == "trial"
    assert all(v["title"] == "试拍" for v in project(page)["versions"])
    passed("early feedback retains co-creation gates; stopped trial revision resumes to trial review")

    # Only the explicitly allowed frontend files can be read through the server.
    for route in ["/.env.example", "/AGENTS.md", "/../package.json", "/state.js/../server.mjs"]:
        assert page.request.get(BASE + route).status == 404
    assert not external, external
    assert not errors, errors
    passed("loopback static allowlist, no external browser requests, no uncaught JS errors")
    (OUT / "browser-results.json").write_text(json.dumps({
        "checks": checks, "count": len(checks), "errors": errors,
        "external_requests": external, "browser": browser.version,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scope": "Simulated UI only; no model, real media, or human film-quality validation",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    browser.close()
