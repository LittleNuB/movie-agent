"""Focused API settings UI checks. Run with the local prototype server active."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('PROTOTYPE_URL', 'http://127.0.0.1:4317')
OUT = Path('.cache/prototype/model-settings')
OUT.mkdir(parents=True, exist_ok=True)
checks, errors, external = [], [], []
DEMO_KEY = 'demo-credential-for-ui-check-only'


def record(name):
    checks.append(name)
    print('PASS', name, flush=True)


def config(page):
    return page.evaluate("JSON.parse(localStorage.getItem('movie-agent.prototype.v1')).modelSettings")


def action(page, name):
    page.locator(f'[data-api="{name}"]').first.click()


def add_model(page, model_id, capability, label=''):
    action(page, 'add-model')
    row = page.locator('[data-model]').last
    row.get_by_role('textbox', name='模型 ID', exact=True).fill(model_id)
    row.get_by_role('textbox', name='模型显示名称', exact=True).fill(label)
    row.get_by_role('combobox', name='模型能力', exact=True).select_option(capability)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1000}, color_scheme='light')
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: external.append(r.url) if not r.url.startswith(BASE) else None)
    page.goto(BASE, wait_until='networkidle')
    page.get_by_role('button', name='打开示例影片', exact=True).click()
    page.get_by_role('tab', name='剧本', exact=True).click()
    script = page.get_by_role('textbox', name='剧本编辑器')
    changed = script.input_value() + '\n设置修改期间应保留的手改稿。'
    script.fill(changed)
    page.locator('[data-action="settings"]').first.click()
    expect(page.get_by_role('heading', name='模型与 API')).to_be_visible()
    expect(page.locator('[data-api="save"]')).to_be_in_viewport(ratio=1)
    assert config(page) == {'connections':[], 'assignments':{}}
    expect(page.locator('#api-url')).to_have_value('')
    expect(page.locator('#api-key')).to_have_attribute('type', 'password')
    assert page.locator('[data-model]').count() == 0
    assert not any(s in page.locator('dialog').inner_text() for s in ['MiniMax','GLM','Seedream','Seedance'])
    action(page, 'assignments')
    assert all(v == '' for v in page.locator('[data-purpose]').evaluate_all('els=>els.map(e=>e.value)'))
    action(page, 'connections')
    record('empty provider/model/purpose defaults; no personal model names in product settings')

    page.get_by_label('连接名称', exact=True).fill('我的创作服务')
    page.get_by_label('API 地址 · Base URL', exact=True).fill('https://api.example.com/v1')
    page.get_by_label('API Key', exact=True).fill(DEMO_KEY)
    action(page, 'toggle-key')
    expect(page.locator('#api-key')).to_have_attribute('type', 'text')
    action(page, 'toggle-key')
    expect(page.locator('#api-key')).to_have_attribute('type', 'password')
    action(page, 'check')
    expect(page.locator('#api-check-result')).to_contain_text('模拟连接成功')
    page.locator('.api-test-options summary').click()
    page.locator('#api-simulate-failure').check()
    action(page, 'check')
    expect(page.locator('#api-check-result')).to_contain_text('模拟失败')
    page.locator('#api-simulate-failure').uncheck()
    action(page, 'check')
    page.locator('#api-url').fill('https://api.example.com/custom/v1')
    page.wait_for_timeout(650)
    expect(page.locator('#api-check-result')).to_contain_text('检查结果已失效')
    record('editable masked key; simulated success/failure; stale check invalidated on edit')

    action(page, 'discover')
    expect(page.locator('#api-check-result')).to_contain_text('已加入 1 个示例模型')
    row=page.locator('[data-model]').first
    row.get_by_role('textbox', name='模型 ID', exact=True).fill('my-chat-model')
    row.get_by_role('textbox', name='模型显示名称', exact=True).fill('创作对话')
    row.get_by_role('combobox', name='模型能力', exact=True).select_option('text')
    add_model(page, 'my-image-model', 'image', '画面参考')
    add_model(page, 'my-video-model', 'video', '动态片段')
    action(page, 'save')
    assert len(config(page)['connections']) == 1
    first_id = config(page)['connections'][0]['id']
    assert len(config(page)['connections'][0]['models']) == 3
    assert DEMO_KEY not in page.evaluate('JSON.stringify(localStorage)')
    # Key masking is checked before screenshots; only fake data is ever entered.
    expect(page.locator('#api-key')).to_have_attribute('type', 'password')
    page.locator('.api-editor').evaluate('(e)=>e.scrollTop=0')
    page.wait_for_timeout(200)
    page.screenshot(path=str(OUT/'connections-day.png'))
    record('editable discovery and manual IDs; multiple models in one connection; key excluded from storage')

    action(page, 'assignments')
    assert page.locator('#purpose-director option').count() == 2
    assert page.locator('#purpose-video option').count() == 2
    page.locator('#purpose-director').select_option(index=1)
    page.locator('#purpose-image').select_option(index=1)
    page.locator('#purpose-video').select_option(index=1)
    action(page, 'save-assignments')
    assert len(config(page)['assignments']) == 3
    assert config(page)['assignments']['director'].startswith(first_id+'/')
    record('purpose choices filtered by declared capability, explicitly saved without generation')

    action(page, 'connections')
    action(page, 'new')
    page.locator('#api-name').fill('本机另一连接')
    page.locator('#api-protocol').select_option('custom')
    page.locator('#api-url').fill('http://127.0.0.1:1234/v1')
    page.locator('#api-no-key').check()
    expect(page.locator('#api-key')).to_be_disabled()
    expect(page.locator('#api-protocol-note')).to_contain_text('需相应适配器')
    action(page, 'check')
    expect(page.locator('#api-check-result')).to_contain_text('模拟连接成功')
    add_model(page, 'my-chat-model', 'text', '另一个对话模型')
    action(page, 'save')
    assert len(config(page)['connections']) == 2
    record('multiple connections with duplicate model IDs kept separate; no-key option and adapter boundary')

    page.locator('[data-api="select"][data-id="'+first_id+'"]').click()
    # Remove only the video model; its assignment must not silently switch.
    page.locator('[data-model]').last.locator('[data-api="remove-model"]').click()
    action(page, 'save')
    assert 'video' not in config(page)['assignments']
    assert 'director' in config(page)['assignments']
    page.locator('#api-url').fill('https://user:password@example.com/v1')
    action(page, 'save')
    expect(page.locator('#api-form-error')).to_contain_text('不要在地址中放账号')
    assert config(page)['connections'][0]['baseUrl'] == 'https://api.example.com/custom/v1'
    page.locator('#api-url').fill('https://api.example.com/custom/v1')
    action(page, 'delete')
    assert config(page)['assignments'] == {}
    assert len(config(page)['connections']) == 1
    record('model/connection removal clears only affected assignments; credentials-in-URL rejected')

    page.locator('[data-action="dialog-close"]').click()
    expect(page.get_by_role('textbox', name='剧本编辑器')).to_have_value(changed)
    page.locator('[data-action="theme"]').click()
    page.locator('[name="theme"][value="dark"]').check()
    page.locator('[data-action="theme-save"]').click()
    page.reload(wait_until='networkidle')
    expect(page.get_by_role('textbox', name='剧本编辑器')).to_have_value(changed)
    page.locator('[data-action="settings"]').first.click()
    expect(page.locator('#api-key')).to_have_value('')
    assert len(config(page)['connections']) == 1
    assert config(page)['connections'][0]['name'] == '本机另一连接'
    page.screenshot(path=str(OUT/'connections-night.png'))
    action(page, 'assignments')
    page.screenshot(path=str(OUT/'assignments-night.png'))
    record('refresh preserves metadata and creative drafts, clears key, maintains night theme')

    page.set_viewport_size({'width':1280,'height':800})
    action(page, 'connections')
    expect(page.locator('[data-api="save"]')).to_be_in_viewport(ratio=1)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    assert not external, external
    record('desktop layout, no external requests or uncaught JS errors')
    (OUT/'results.json').write_text(json.dumps({'checks':checks,'count':len(checks),'errors':errors,'external_requests':external,'browser':browser.version},indent=2),encoding='utf-8')
    browser.close()
