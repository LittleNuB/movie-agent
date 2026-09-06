import { uid, clockTime, modeLabel, modeDescription, director, user, stamp, createProject, makeReview, openTab, load, save } from './state.js';
import { drawFilm, DemoSound } from './film-art.js';

const state = load();
const app = document.querySelector('#app');
const dialog = document.querySelector('#dialog');
const sound = new DemoSound();
const symbols = {
  plus:'M12 5v14M5 12h14', close:'m6 6 12 12M18 6 6 18',
  panel:'M4 4h16v16H4zM9 4v16', work:'M4 4h16v16H4zM15 4v16',
  arrow:'M12 19V5m-6 6 6-6 6 6', down:'m7 10 5 5 5-5', right:'m9 5 7 7-7 7',
  script:'M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6',
  image:'M3 4h18v16H3zM3 16l6-6 5 5 3-3 4 4M16 8h.01',
  film:'M4 5h16v14H4zM8 5v14M16 5v14M4 9h4M4 15h4M16 9h4M16 15h4',
  play:'m9 5 11 7-11 7z', pause:'M8 5v14M16 5v14', stop:'M6 6h12v12H6z',
  sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1 1M18 18l1 1M5 19l1-1M18 6l1-1',
  moon:'M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11', settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2',
  note:'M4 4h16v12H9l-5 4zM8 8h8M8 12h5', history:'M3 4v5h5M3 9a9 9 0 1 1 1 8M12 7v6l4 2',
  more:'M5 12h.01M12 12h.01M19 12h.01', check:'m5 12 4 4L19 6',
  download:'M12 3v12m-5-5 5 5 5-5M5 17v4h14v-4',
  volume:'M3 9h4l5-4v14l-5-4H3zM16 8a6 6 0 0 1 0 8M19 5a10 10 0 0 1 0 14',
  mute:'M3 9h4l5-4v14l-5-4H3zM16 9l5 6M21 9l-5 6',
  expand:'M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5',
  sparkle:'m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z',
  logo:'M5 18V6l7 9 7-9v12', pencil:'m4 16 12-12 4 4L8 20H4zM14 6l4 4',
};
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${symbols[name] || symbols.film}"/></svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
const ib = (action, name, label, data = '') => `<button class="icon-button" data-action="${action}" ${data} title="${label}" aria-label="${label}">${icon(name)}</button>`;
const pNow = () => state.projects.find(p => p.id === state.activeId);
let playing = false, playbackVersion = null, lastFrame = performance.now(), lastStored = 0, muted = true, toastTimeout;
let storageFailed = false;
const renderedMessages = new Set();

function persist() {
  if (!save(state) && !storageFailed) { storageFailed = true; notice('浏览器未能保存草稿，请先下载保留。当前页面仍可继续使用。'); }
}
function notice(message) {
  const box = document.querySelector('#notice'); box.textContent = message; box.classList.add('visible');
  clearTimeout(toastTimeout); toastTimeout = setTimeout(() => box.classList.remove('visible'), 3600);
}
function setTheme() {
  const theme = state.theme === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : state.theme;
  document.documentElement.dataset.theme = theme;
}
setTheme(); matchMedia('(prefers-color-scheme: dark)').addEventListener('change', setTheme);

function status(p) {
  if (p.task) return p.task.status === 'stopping' ? '正在停止' : '制作中';
  if (p.pending) return '待审核';
  return ({ finished:'已完成', stopped:'已停止', failed:'待继续', proposal:'草稿', trial:'试拍完成' }[p.stage] || '创作中');
}
function assetName(kind) { return ({ proposal:'故事提案', script:'剧本', visual:'视觉方案', video:'试拍', backup:'保留的草稿' }[kind] || kind); }
function version(p, id) { return p.versions.find(v => v.id === id); }
function tabTitle(p, t) {
  if (t.kind === 'video') { const v = version(p, t.id); return v ? `${v.title} · 第 ${v.number} 版` : '影片'; }
  if (t.kind === 'backup') return '保留的手改稿';
  return assetName(t.kind);
}
function reviewName(p, r) {
  const v = version(p, r.versionId);
  if (r.kind === 'trial') return `${v?.title || '试拍'} · 第 ${v?.number || 1} 版`;
  return ({ proposal:'故事提案 · 本次提交', script:'剧本 · 本次提交', visual:'人物与场景 · 第 1 版', revision:'修改方案 · 本次反馈' }[r.kind]);
}
function reviewAsset(r) { return ({ trial:'video', revision:r.snapshot ? 'script' : 'video', proposal:'proposal', script:'script', visual:'visual' }[r.kind]); }

function sidebar(p) {
  return `<aside class="sidebar" aria-label="影片导航">
    <div class="brand"><div class="brand-mark">${icon('logo')}</div><strong>影片创作</strong></div>
    <button class="new-project" data-action="new">${icon('plus')}<span>新建影片</span></button>
    <div class="sidebar-content"><div class="section-label"><span>我的影片</span><span>${state.projects.length}</span></div>
    ${[...state.projects].sort((a,b) => b.updated-a.updated).map(x => `<button class="project-item ${x.id===p?.id?'active':''} ${x.task?'working':''}" data-action="project" data-id="${x.id}" ${x.id===p?.id?'aria-current="page"':''}><strong>${esc(x.title)}</strong><small><i class="status-dot ${x.pending?'waiting':''}"></i>${status(x)}${x.title==='最后一束光'?' · 示例':''}</small></button>`).join('')}</div>
    <div class="sidebar-bottom"><button class="text-button" data-action="settings">${icon('settings')}<span class="hide-collapsed">模型设置</span></button>
    <button class="text-button" data-action="theme">${icon(document.documentElement.dataset.theme==='dark'?'moon':'sun')}<span class="hide-collapsed">外观</span></button>
    <button class="text-button" data-action="nav">${icon('panel')}<span class="hide-collapsed">收起侧栏</span></button>
    <span class="local-note hide-collapsed"><i class="status-dot"></i>本地交互原型</span></div></aside>`;
}

function renderMessage(p, m) {
  const fresh=renderedMessages.has(m.id)?'':'fresh'; renderedMessages.add(m.id);
  if (m.role === 'user') return `<article class="message user ${fresh}"><div class="user-bubble">${(m.annotations || []).map(a => `<div class="sent-ref">${clockTime(a.time)} · 第 ${version(p,a.versionId)?.number || '?'} 版<br>${esc(a.text)}</div>`).join('')}${esc(m.text)}</div></article>`;
  const r = m.review; const active = r && p.pending?.id === r.id;
  return `<article class="message director ${fresh}"><div class="director-byline"><span class="director-avatar">${icon('logo')}</span>导演</div>
    <div class="message-text">${esc(m.text)}</div>
    ${m.assets ? `<div class="artifact-links">${m.assets.filter(kind=>kind!=='video'||version(p,m.versionId)).map(kind=>`<button class="artifact-link" data-action="asset" data-kind="${kind}" data-id="${kind==='video'?m.versionId:''}">${icon(kind==='proposal'?'script':kind==='visual'?'image':kind==='video'?'film':kind)}${assetName(kind)} ${icon('right')}</button>`).join('')}</div>`:''}
    ${r?`<div class="review" data-review="${r.id}"><div class="review-top"><strong>${reviewName(p,r)}</strong><span class="review-state">${active?'等你确认':'已处理或已替代'}</span></div>
      <p>${r.kind==='revision'?(r.scope==='audio'?'只调整示例声音方向，保留当前画面。':'按本次提交的内容更新示例版本，保留已有作品。'):'查看对应内容后，可以确认继续，也可以直接在对话里说修改意见。'}</p>
      <div class="review-actions"><button class="button" data-action="review-view" data-id="${r.id}">${icon('script')}查看内容</button><button class="button primary" data-action="approve" data-id="${r.id}" ${active?'':'disabled'}>确认并继续 ${icon('right')}</button></div></div>`:''}</article>`;
}

function welcome() {
  return `<div class="welcome"><div class="welcome-inner"><div class="welcome-orbit"><div class="brand-mark">${icon('logo')}</div></div>
    <div class="eyebrow" style="margin-bottom:12px">A STORY STARTS WITH YOU</div><h1>你想拍一个怎样的故事？</h1><p>一句话、一个画面，或一种感受都可以。<br>我们一起把它慢慢拍出来。</p>
    <div class="examples"><button class="example" data-action="example" data-index="0">${icon('plus')}宇宙里的一个人，等一束迟来的光</button><button class="example" data-action="example" data-index="1">${icon('plus')}末日之前，父亲想给孩子看一次真正的日出</button></div>
    <div class="welcome-actions"><button class="button" data-action="demo">${icon('play')}打开示例影片</button><button class="text-button" data-action="settings">配置模型 ${icon('right')}</button></div></div></div>`;
}

function annotations(p) {
  return (p?.annotations || []).map(a=>`<div class="annotation-draft" data-annotation="${a.id}"><button class="annotation-ref" data-action="annotation-jump" data-id="${a.id}">${clockTime(a.time)} · 第 ${version(p,a.versionId)?.number || '?'} 版</button><textarea aria-label="标注意见" data-annotation-input="${a.id}" rows="1">${esc(a.text)}</textarea><div class="annotation-actions">${ib('annotation-send','arrow','单独发送此标注',`data-id="${a.id}"`)}${ib('annotation-remove','close','移除此标注',`data-id="${a.id}"`)}</div></div>`).join('');
}
function composer(p) {
  return `<div class="composer-zone"><div class="composer"><div id="annotation-drafts">${annotations(p)}</div><textarea id="composer-input" aria-label="给导演的消息" placeholder="${p?'说说你的想法，或给作品一些修改意见…':'从你的第一个想法开始…'}" rows="2">${esc(p?.composer ?? state.welcomeDraft)}</textarea>
    <div class="composer-footer"><button class="mode-button" data-action="mode">${icon('sparkle')}<span>${modeLabel(p?.mode || state.defaultMode)}</span>${icon('down')}</button><div class="send-controls">${p?.task?`<button class="stop" data-action="stop" ${p.task.status==='stopping'?'disabled':''}>${icon('stop')}${p.task.status==='stopping'?'正在停止':'中止'}</button>`:''}<button class="icon-button send" data-action="send" aria-label="发送消息" title="发送 · Enter">${icon('arrow')}</button></div></div></div><p class="composer-caption">交互原型 · 示例内容与回复 · 不调用真实模型</p></div>`;
}

function work(p) {
  const t = p.tabs.find(t=>t.key===p.activeTab);
  return `<aside class="work-pane" aria-label="作品侧栏"><div class="work-header"><div><strong style="font-weight:500;font-size:13px">作品</strong><button class="text-button" data-action="library">目录 ${icon('down')}</button></div><div>${ib('library','plus','打开作品目录')}${ib('work-close','work','收起作品侧栏')}</div></div>
    <div class="tabs" role="tablist" aria-label="作品标签">${p.tabs.map(x=>`<div class="tab ${t?.key===x.key?'active':''}"><button role="tab" aria-selected="${t?.key===x.key}" data-action="tab" data-key="${x.key}">${tabTitle(p,x)}</button>${ib('tab-close','close',`关闭${tabTitle(p,x)}`,`data-key="${x.key}"`)}</div>`).join('')}</div>
    <div class="artifact-body" id="artifact-body">${t?renderArtifact(p,t):`<div class="empty-artifact"><p>剧本、画面与影片，都在这里。</p><button class="button" data-action="library">打开作品目录</button></div>`}</div></aside>`;
}

function renderArtifact(p, t) {
  if (t.kind==='proposal') return `<div class="document"><div class="document-top"><span class="eyebrow">STORY PROPOSAL / 示例</span><button class="text-button" data-action="proposal-edit">${icon('pencil')}编辑</button></div>${p.proposal.split('\n\n').map((x,i)=> i===0?`<h1>${esc(x)}</h1>`:['完整故事','准备怎样拍'].includes(x)?`<h2>${x}</h2>`:`<p>${esc(x)}</p>`).join('')}</div>`;
  if (t.kind==='script') return `<div class="script-pane"><div class="script-toolbar"><div class="save-state"><span id="save-status" style="font-size:11px;color:var(--muted)">${p.draftScript===p.appliedScript?'已保存 · 当前制作稿':'已保存 · 有修改未提交'}</span></div><button class="text-button" data-action="script-download" title="下载当前草稿">${icon('download')}</button><button class="button primary" data-action="script-submit">提交修改 ${icon('arrow')}</button></div><textarea class="script-editor" id="script-editor" aria-label="剧本编辑器" spellcheck="false">${esc(p.draftScript)}</textarea>${p.draftBackups.length?`<div class="draft-backup">已保留 ${p.draftBackups.length} 份手改稿。<button class="text-button" data-action="backups">查看</button></div>`:''}<div class="artifact-footnote">自动保存到本浏览器。提交后先由导演理解，确认方案后再调整作品。</div></div>`;
  if (t.kind==='backup') { const b=p.draftBackups.find(b=>b.id===t.id); return `<div class="document"><div class="document-top"><span class="eyebrow">保留的手改稿 · 只读</span><button class="button" data-action="backup-restore" data-id="${t.id}">恢复到编辑器</button></div><p style="white-space:pre-wrap">${esc(b?.text)}</p></div>`; }
  if (t.kind==='visual') return `<div class="document"><div class="document-top"><span class="eyebrow">VISUAL DIRECTION / 01</span><span class="pill">示意图</span></div><h1>让光，成为回答。</h1><p>先看到一个人，再看到她身后的宇宙。</p><figure class="visual-figure"><canvas id="visual-canvas" aria-label="轨道站、宇航员与地球日出的原创示意图"></canvas><figcaption><span>01 · 林遥 / 轨道中继站</span><span>日出前的冷与暖</span></figcaption></figure><div class="swatches"><i style="background:#0b1b23"></i><i style="background:#334a58"></i><i style="background:#7193a4"></i><i style="background:#cbb995"></i><i style="background:#e8d4ac"></i></div><div class="meta-grid"><div><span>人物与连续性</span><p>灰白舱内服、旧台灯、背部设备保持一致。动作克制，情绪留在手和停顿里。</p></div><div><span>画面与声音</span><p>舷窗形成画中框；冷色环境里只留一处暖光。呼吸与机器声先于音乐。</p></div></div><p class="media-disclosure">原创程序示意图，仅用于查看与审核交互。电影质感需后续真实生成验证。</p></div>`;
  if (t.kind==='video') {
    const v=version(p,t.id); if (!v) return '<div class="empty-artifact">此示例版本不可用。</div>';
    const time=p.playheads[v.id] || 0;
    return `<div class="video-document"><div class="video-heading"><div><h2>${esc(p.title)}</h2><small>${v.title} · 第 ${v.number} 版 &nbsp; / &nbsp; 01:40</small></div><span class="pill">${p.adoptedId===v.id?'当前采用':'历史查看'}</span></div><div class="player" id="player"><div class="frame"><canvas class="film-canvas" id="film-canvas" aria-label="可播放的原创动态示意画面"></canvas><span class="frame-caption">示例动态画面 · 非生成影片</span></div><div class="player-bar">${ib('play',playing&&playbackVersion===v.id?'pause':'play',playing?'暂停示例':'播放示例')}<span class="time-display"><strong id="play-time">${clockTime(time)}</strong> / 01:40</span><input id="seek" type="range" min="0" max="100" step="0.1" value="${time}" aria-label="播放进度">${ib('mute',muted?'mute':'volume',muted?'开启示例环境声':'关闭示例环境声')}${ib('fullscreen','expand','全屏预览')}</div></div><div class="video-actions"><button class="button" data-action="annotate">${icon('note')}添加标注</button><button class="text-button" data-action="history">${icon('history')}历史版本</button></div>${p.adoptedId!==v.id?`<div style="margin-top:16px"><button class="button" data-action="version-continue" data-id="${v.id}">从此版本继续 ${icon('right')}</button></div>`:''}<div class="video-note"><strong>这一版的变化</strong>${esc(v.note)}<br>${v.treatment==='quiet'?'给等待多留一点空间。声音的轻重，需要放回画面里一起判断。':'从一个具体的动作开始，等待最后的信号。'}</div><p class="media-disclosure">画面为原创程序动画，声音为合成低鸣。播放、字幕与时间点可操作；此处不展示真实 AIGC 画质或配乐修改效果。</p></div>`;
  }
  return '';
}

function render({ bottom = false } = {}) {
  const focused=document.activeElement;
  const focusId=focused?.id;
  const annotationFocus=focused?.dataset?.annotationInput;
  const selection=focused instanceof HTMLTextAreaElement?[focused.selectionStart,focused.selectionEnd]:null;
  const oldScroll = document.querySelector('.conversation')?.scrollTop || 0;
  const p=pNow();
  app.innerHTML=`<div class="shell ${p?.workOpen?'with-work':''} ${state.navOpen?'':'nav-closed'}">${sidebar(p)}<main class="chat-pane"><header class="chat-header"><div class="title-group">${p?`<button class="project-title" data-action="rename">${esc(p.title)}</button><span class="eyebrow">${status(p)} · 示例项目</span>`:'<span class="project-title">新影片</span>'}</div><span class="prototype-label">交互原型</span>${p?ib('work-open','work','打开作品侧栏'):''}${ib('demo-menu','more','演示选项')}</header>${p?`<div class="conversation" id="conversation"><div class="chat-body">${p.messages.map(m=>renderMessage(p,m)).join('')}${p.task?`<details class="progress"><summary>${p.task.status==='stopping'?'正在停止示例制作…':'示例制作中…'} · 展开进展</summary><p>已保留当前作品。正在演示${p.task.kind==='visual'?'视觉准备':p.task.kind==='trial'?'试拍':p.task.kind==='film'?'影片合成':'修改制作'}的等待状态。<br>本页面使用计时器推进，未提交外部媒体任务。</p></details>`:''}</div></div>`:welcome()}${composer(p)}</main>${p?.workOpen?work(p):''}</div>`;
  const conversation=document.querySelector('.conversation');
  if(conversation) conversation.scrollTop=bottom?conversation.scrollHeight:oldScroll;
  document.querySelector('.tabs [aria-selected="true"]')?.scrollIntoView({block:'nearest',inline:'nearest'});
  const tab=p?.tabs.find(t=>t.key===p.activeTab);
  if(tab?.kind==='video'&&p.workOpen) drawFilm(document.querySelector('#film-canvas'),p.playheads[tab.id]||0,version(p,tab.id)?.treatment);
  if(tab?.kind==='visual'&&p.workOpen) drawFilm(document.querySelector('#visual-canvas'),58,'quiet',true);
  if(!(tab?.kind==='video'&&p?.workOpen&&tab.id===playbackVersion)) pause();
  const nextFocus=annotationFocus?document.querySelector(`[data-annotation-input="${annotationFocus}"]`):focusId?document.getElementById(focusId):null;
  if(nextFocus&&selection) { nextFocus.focus({preventScroll:true}); nextFocus.setSelectionRange(...selection); }
}

function pause() { playing=false; sound.stop(); }
function commitRender(options={}) { persist(); render(options); }
function modal(title,body) {
  dialog.innerHTML=`<div class="dialog-header"><h2 id="dialog-title">${title}</h2>${ib('dialog-close','close','关闭弹窗')}</div><div class="dialog-body">${body}</div>`;
  if(!dialog.open) dialog.showModal();
}
function closeModal() { dialog.close(); }
function openAsset(kind,id='') { const p=pNow(); if(!p) return; openTab(p,kind,id|| (kind==='video'?p.adoptedId:'')); commitRender(); }
function touch(p) { p.updated=Date.now(); }

// Demo flow: small, explicit state transitions. These do not implement a director model.
const phaseOf = p => p.pending?.kind==='trial'||p.pending?.reviewAfter==='trial' ? 'trial' : p.task?.phase || p.pausedTask?.phase || p.stage;
function task(p,kind,plan={}) {
  const phase=phaseOf(p); p.pending=null; p.task={id:uid(),kind,phase,status:'running',due:Date.now()+(kind==='film'||kind==='revision'?12000:5500),plan}; p.pausedTask=null;
  p.messages.push(director(`我会${kind==='visual'?'先准备人物与场景的视觉方向':kind==='trial'?'准备一段代表性试拍':kind==='film'?'继续完成影片':plan.scope==='audio'?'按方案调整声音，保留画面':'按确认的方案调整作品'}。你可以继续发消息，也可以中止。（本次为示例制作演示。）`)); touch(p);
}
function maybeDelegated(p) {
  if(p.pending && (p.mode==='auto'||p.mode==='audio'&&p.pending.scope==='audio')) {
    p.messages.push(director(`这项工作在你${p.mode==='auto'?'托管':'声音托管'}的授权内，我会继续推进。`));
    approve(p,p.pending.id);
  }
}
function applySnapshot(p,snapshot) {
  if(snapshot!==undefined) p.appliedScript=snapshot;
  // The editor is intentionally untouched: a later manual edit must survive.
}
function approve(p,id) {
  const r=p.pending; if(!r||r.id!==id) { notice('这轮方案已处理或被新的反馈替代，请查看最新建议。'); return; }
  p.pending=null;
  if(r.kind==='proposal') {
    p.scriptAvailable=true; p.stage='script';
    makeReview(p,'script','我把故事展开成了分场剧本。请看她接上电缆的动作是否足够清楚，以及最后一句话是否需要保留。确认后，我会准备人物与场景的视觉方向。',{snapshot:p.draftScript});
    openTab(p,'script','',false); maybeDelegated(p);
  } else if(r.kind==='script') { applySnapshot(p,r.snapshot); task(p,'visual'); }
  else if(r.kind==='visual') task(p,'trial');
  else if(r.kind==='trial') task(p,'film',{baseId:r.versionId});
  else if(r.kind==='revision') task(p,'revision',r);
}

function finishTask(p) {
  const t=p.task; p.task=null;
  if(t.status==='stopping') { p.pausedTask=t; p.stage='stopped'; p.messages.push(director('示例制作已停止。对话、手改稿和已有作品都保留了。你可以先看一看，再告诉我是否继续。这里没有外部生成任务需要取消。')); return; }
  if(t.kind==='visual') {
    p.visualReady=true; p.stage='visual'; makeReview(p,'visual','我把人物放回她实际所在的舱内：冷色环境、灰色服装，只留台灯与日出的暖光。请看外观与场景气质，确认后进入试拍。'); openTab(p,'visual','',false);
  } else {
    const base=version(p,t.plan.baseId)||version(p,p.adoptedId);
    if(t.kind==='revision') applySnapshot(p,t.plan.snapshot);
    const isTrial=t.kind==='trial'||t.plan.reviewAfter==='trial';
    const v={id:uid(),number:Math.max(0,...p.versions.map(v=>v.number))+1,title:isTrial?'试拍':'影片',note:t.kind==='trial'?'人物与环境的首次动态试拍':t.kind==='revision'?(t.plan.scope==='audio'?'根据声音反馈调整示例方向，沿用原画面':'根据本次方案更新示例作品'):'完成示例影片，保持已确认的声画方向',script:p.appliedScript||p.draftScript,created:stamp(),treatment:t.plan.scope==='audio'?'quiet':base?.treatment||'quiet',parentId:base?.id};
    p.versions.push(v); p.adoptedId=v.id; p.playheads[v.id]=0;
    p.messages.push(director(`第 ${v.number} 版示例已准备好。${t.kind==='revision'?'原来的版本和未提交的手改稿仍然保留。':'可以打开预览，把需要调整的位置标注给我。'}`,{assets:['video'],versionId:v.id}));
    if(isTrial) { p.stage='trial'; makeReview(p,'trial','请结合画面和声音看一遍。你认可后，我会继续完成影片。',{versionId:v.id}); }
    else p.stage='finished';
    openTab(p,'video',v.id,false);
  }
  touch(p); maybeDelegated(p);
}

function submitScript(p) {
  if(!p?.scriptAvailable) return;
  const phase=phaseOf(p);
  if(p.task) { p.task=null; p.messages.push(director('收到新改稿，这轮示例制作先停在已有版本。接下来按本次提交讨论修改方案。')); }
  p.messages.push(user('请理解并应用我刚提交的剧本修改。'));
  p.pausedTask=null;
  makeReview(p,p.versions.length?'revision':'script','我收到这份改稿了。建议先按提交内容更新制作稿，再检查相关画面和声音的衔接。此原型展示理解、建议与确认的流程；实际修改范围将由接入后的导演判断。',{scope:'story',snapshot:p.draftScript,baseId:p.adoptedId,reviewAfter:phase==='trial'?'trial':undefined});
  maybeDelegated(p); touch(p); commitRender({bottom:true});
}

function changeMode(mode, p=pNow()) {
  if(p) { p.mode=mode; p.messages.push(director(`当前模式：${modeLabel(mode)}。${modeDescription(mode)}`)); touch(p); maybeDelegated(p); }
  else state.defaultMode=mode;
  commitRender({bottom:true});
}

function send(singleId) {
  let p=pNow(); const message=(p?.composer ?? state.welcomeDraft).trim();
  const refs=p?(singleId?p.annotations.filter(a=>a.id===singleId):p.annotations):[];
  if(!message&&!refs.length) { document.querySelector('#composer-input')?.focus(); return; }
  if(refs.some(a=>!a.text.trim())) { notice('请先写下标注意见，或移除空标注。'); return; }
  if(!p) {
    p=createProject('未命名影片',state.defaultMode); state.projects.push(p); state.activeId=p.id; state.welcomeDraft='';
    p.messages.push(user(message));
    p.messages.push(director('我听到了你的想法。这里先以《最后一束光》的示例故事，带你走一遍讨论、审核和拍摄的过程；真实接入后，提案会围绕你的输入展开。'));
    makeReview(p,'proposal','先看这个故事是否值得拍：用一次具体的选择，承接最后一点希望。认可这个方向后，我会把它展开成剧本。',{snapshot:p.proposal});
    openTab(p,'proposal','',false); maybeDelegated(p); commitRender({bottom:true}); return;
  }
  const text=singleId?'':message;
  p.messages.push(user(text,{annotations:refs.map(a=>({...a}))}));
  p.annotations=p.annotations.filter(a=>!refs.some(r=>r.id===a.id)); if(!singleId) p.composer=''; touch(p);
  if(!refs.length&&/^(切换到?|改为|用)?(共创|托管|全权托管|声音托管)[吧。！!]?$/u.test(text)) {
    changeMode(text.includes('声音')?'audio':text.includes('托管')?'auto':'co',p); return;
  }
  if(!refs.length&&/^(请)?(提交修改|应用改稿|应用剧本修改)[。！!]?$/u.test(text)) { submitScript(p); return; }
  if(!refs.length&&/^(同意|确认|认可|确认并继续|继续|可以)[。！!]?$/u.test(text)) {
    if(p.pending) approve(p,p.pending.id);
    else if(['stopped','failed'].includes(p.stage)) {
      if(p.pausedTask) task(p,p.pausedTask.kind,p.pausedTask.plan);
      else if(!p.scriptAvailable) makeReview(p,'proposal','先继续这份示例提案。认可故事方向后，再展开剧本。',{snapshot:p.proposal});
      else if(!p.visualReady) makeReview(p,'script','先确认这份剧本，再准备人物与场景的视觉方向。',{snapshot:p.draftScript});
      else task(p,p.versions.length?'film':'trial',{baseId:p.adoptedId});
    }
    else p.messages.push(director(p.task?'这轮示例正在制作，消息已经收到了。你可以展开进展，或打开现有作品。':'这轮示例已完成。你可以查看作品，或告诉我想修改哪里。'));
  } else if(!refs.length&&/^(停止|中止|停一下)[。！!]?$/u.test(text)) requestStop(p);
  else if(!refs.length&&/(进度|多久|在做什么)/u.test(text)) p.messages.push(director(p.task?'这轮示例还在制作中，已经完成的作品可以随时打开。本页用短计时演示等待，不代表真实制作速度。':'目前没有运行中的示例任务。已有作品和草稿都保存在这个项目里。'));
  else {
    const phase=['proposal','script','visual'].includes(p.pending?.kind)?p.pending.kind:phaseOf(p);
    if(p.task) { p.task=null; p.messages.push(director('我先暂停这轮示例制作，保留已有结果，和你确认新的修改方向。')); }
    p.pausedTask=null;
    const content=[text,...refs.map(a=>a.text)].join(' ');
    const scope=/(音乐|配乐|环境声|音量)/u.test(content)&&!/(台词|对白|口型|剧情|剧本|画面|镜头)/u.test(content)?'audio':'story';
    if(['proposal','script','visual'].includes(phase)&&!p.versions.length) {
      p.stage=phase;
      makeReview(p,phase,`我收到这轮修改意见了。我们先留在${assetName(phase)}讨论，把方向确认清楚，再往后推进。此原型保留固定示例内容，你也可以手动改写文字；后续审核仍按共创授权进行。`,{scope:phase==='visual'?'visual':'story',snapshot:phase==='proposal'?p.proposal:phase==='script'?p.draftScript:undefined,feedback:text});
    } else makeReview(p,'revision',scope==='audio'?'我理解你想把声音再收一点。建议沿用画面，让配乐更晚进入，并把环境声留在前面。你确认后，我会按这个方向推进。':'我收到了这些想法。建议把这轮意见作为一次完整修改，保留当前作品作对照，再检查故事、画面和声音是否需要一起变化。这是示例修改建议，尚未调用导演模型。',{scope,baseId:refs[0]?.versionId || p.adoptedId,refs:refs.map(a=>({...a})),feedback:text,reviewAfter:phase==='trial'?'trial':undefined});
    maybeDelegated(p);
  }
  commitRender({bottom:true});
}

function requestStop(p) {
  if(!p.task) { p.messages.push(director('当前没有运行中的示例制作。已有内容已保留。')); return; }
  p.task.status='stopping'; p.task.due=Date.now()+1400;
  p.messages.push(director('已收到停止请求，正在结束这轮示例制作。'));
}

function settings() {
  modal('模型设置',`<p>正式版本将使用你自己的 API Key。这里仅演示配置与连接检查，不接收真实密钥，也不发送模型请求。</p>
    ${[['director','导演与对话','GLM 5.3 Flash'],['video','视频生成','MiniMax H3'],['image','图像生成','Seedream 5.0 Pro'],['backup','备选视频','Seedance 2.0']].map(([id,title,name])=>`<div class="settings-provider"><label for="demo-${id}">${title}<span>${name}</span></label><div class="credential-row"><input id="demo-${id}" type="text" readonly placeholder="仅使用示例凭据" aria-label="${title}示例凭据"><button class="button" data-action="demo-key" data-id="${id}">填入示例</button><button class="button" data-action="check-key" data-id="${id}" disabled>模拟检查</button></div><div class="check-result" id="check-${id}" role="status">尚未检查</div></div>`).join('')}
    <label class="option"><input type="checkbox" id="simulate-key-failure"><span><strong>演示连接失败</strong><small>检查后显示失败说明，可以关闭此选项重试。</small></span></label><div class="dialog-footer"><button class="button primary" data-action="settings-done">完成设置演示</button></div>`);
}
function modeModal() {
  const selected=pNow()?.mode||state.defaultMode;
  modal('怎样一起创作',`<p>由你决定参与的程度。${pNow()?'本次选择只对当前影片生效。':'新影片会使用这次选择。'}</p>${['co','audio','auto'].map(m=>`<label class="option"><input type="radio" name="mode" value="${m}" ${selected===m?'checked':''}><span><strong>${modeLabel(m)}</strong><small>${modeDescription(m)}</small></span></label>`).join('')}<div class="dialog-footer"><button class="button primary" data-action="mode-save">使用这个模式</button></div>`);
}
function library() {
  const p=pNow(); if(!p) return;
  modal('这部影片的作品',`<p>选择内容，在右侧标签页打开。一次查看一份作品。</p>${[['proposal',true,'故事提案'],['script',p.scriptAvailable,'剧本 · 可编辑'],['visual',p.visualReady,'人物与场景']].filter(x=>x[1]).map(([kind,,label])=>`<button class="asset-row" data-action="library-open" data-kind="${kind}"><span><strong>${label}</strong><small>${kind==='script'?'草稿与制作稿分别保留':'示例内容'}</small></span>${icon('right')}</button>`).join('')}${p.versions.map(v=>`<button class="asset-row" data-action="library-open" data-kind="video" data-id="${v.id}"><span><strong>${v.title} · 第 ${v.number} 版 ${v.id===p.adoptedId?' / 当前采用':''}</strong><small>${esc(v.note)}</small></span>${icon('right')}</button>`).join('')}${p.draftBackups.length?`<button class="asset-row" data-action="backups"><span><strong>保留的手改稿</strong><small>${p.draftBackups.length} 份</small></span>${icon('right')}</button>`:''}`);
}
function history() {
  const p=pNow(); if(!p) return;
  modal('影片版本',`<p>查看旧版不会改变当前作品。需要退回时，在预览中选择“从此版本继续”。</p>${[...p.versions].reverse().map(v=>`<button class="history-row" data-action="library-open" data-kind="video" data-id="${v.id}"><span><strong>${v.title} · 第 ${v.number} 版 ${v.id===p.adoptedId?' / 当前采用':''}</strong><small>${esc(v.note)}</small><small>${new Date(v.created).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})}</small></span>${icon('right')}</button>`).join('')}`);
}
function backupDraft(p) {
  if(p.draftScript!==p.appliedScript && !p.draftBackups.some(b=>b.text===p.draftScript)) p.draftBackups.push({id:uid(),text:p.draftScript,created:stamp()});
}
function downloadText(name,content) {
  const url=URL.createObjectURL(new Blob([content],{type:'text/plain;charset=utf-8'}));
  const a=document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}

document.addEventListener('click', async event => {
  const button=event.target.closest('[data-action]'); if(!button||button.disabled) return;
  const {action,id,kind,key}=button.dataset;
  const p=pNow();
  switch(action) {
    case 'new': pause(); state.activeId=null; commitRender(); break;
    case 'project': pause(); state.activeId=id; commitRender({bottom:true}); break;
    case 'demo': pause(); state.activeId=state.projects.find(x=>x.title==='最后一束光')?.id||state.projects[0]?.id; commitRender({bottom:true}); break;
    case 'nav': state.navOpen=!state.navOpen; commitRender(); break;
    case 'send': send(); break;
    case 'example': {
      state.welcomeDraft=['宇宙里的一个人，等一束迟来的光。我想拍一个安静、最后有一点希望的故事。','末日之前，父亲想给孩子看一次真正的日出。大约 100 秒，有克制的情绪。'][Number(button.dataset.index)];
      commitRender(); document.querySelector('#composer-input').focus(); break;
    }
    case 'rename': modal('影片名称',`<p>名称只用于整理这个示例项目。</p><textarea id="rename-input" class="dialog-textarea" aria-label="影片名称" maxlength="50">${esc(p.title)}</textarea><div class="dialog-footer"><button class="button primary" data-action="rename-save">保存名称</button></div>`); break;
    case 'rename-save': { const title=document.querySelector('#rename-input').value.trim(); if(title) { p.title=title; touch(p); closeModal(); commitRender(); } break; }
    case 'theme': modal('外观',`<p>A 日间与 B 夜间采用同一套布局，选择会保留。</p>${[['system','跟随系统'],['light','A · 日间'],['dark','B · 夜间']].map(([value,label])=>`<label class="option"><input type="radio" name="theme" value="${value}" ${state.theme===value?'checked':''}><span><strong>${label}</strong></span></label>`).join('')}<div class="dialog-footer"><button class="button primary" data-action="theme-save">应用外观</button></div>`); break;
    case 'theme-save': state.theme=document.querySelector('[name="theme"]:checked').value; setTheme(); closeModal(); commitRender(); break;
    case 'settings': settings(); break;
    case 'demo-key': document.querySelector(`#demo-${id}`).value='DEMO-ONLY-NOT-A-KEY'; document.querySelector(`[data-action="check-key"][data-id="${id}"]`).disabled=false; break;
    case 'check-key': {
      const result=document.querySelector(`#check-${id}`); const failed=document.querySelector('#simulate-key-failure').checked;
      button.disabled=true; result.className='check-result'; result.textContent='正在模拟检查…';
      setTimeout(()=>{ if(!result.isConnected) return; result.textContent=failed?'模拟失败：服务暂时不可用。可以检查配置后重试。':'模拟连接成功 · 未向服务商发送请求'; result.className=`check-result ${failed?'':'success'}`; button.disabled=false; },600); break;
    }
    case 'settings-done': state.configured=true; closeModal(); persist(); notice('设置演示已完成。未保存任何真实凭据。'); break;
    case 'mode': modeModal(); break;
    case 'mode-save': { const mode=document.querySelector('[name="mode"]:checked').value; closeModal(); changeMode(mode); break; }
    case 'work-close': p.workOpen=false; p.manuallyClosed=true; pause(); commitRender(); break;
    case 'work-open': p.workOpen=true; p.manuallyClosed=false; commitRender(); if(!p.tabs.length) library(); break;
    case 'asset': openAsset(kind,id); break;
    case 'library': library(); break;
    case 'library-open': closeModal(); openAsset(kind,id); break;
    case 'tab': p.activeTab=key; commitRender(); break;
    case 'tab-close': { const index=p.tabs.findIndex(t=>t.key===key); p.tabs=p.tabs.filter(t=>t.key!==key); if(p.activeTab===key) p.activeTab=p.tabs[Math.min(index,p.tabs.length-1)]?.key || null; commitRender(); break; }
    case 'script-submit': submitScript(p); break;
    case 'script-download': downloadText(`${p.title}-剧本草稿.txt`,p.draftScript); break;
    case 'proposal-edit': modal('编辑故事提案',`<p>保存只保留文字。将修改交给导演后，按当前模式继续。</p><textarea id="proposal-editor" class="dialog-textarea" style="height:340px" aria-label="提案编辑器">${esc(p.proposal)}</textarea><div class="dialog-footer"><button class="button" data-action="proposal-save">保存草稿</button><button class="button primary" data-action="proposal-submit">提交提案修改</button></div>`); break;
    case 'proposal-save': p.proposal=document.querySelector('#proposal-editor').value; closeModal(); commitRender(); notice('提案草稿已保存，尚未提交。'); break;
    case 'proposal-submit': p.proposal=document.querySelector('#proposal-editor').value; closeModal(); p.task=null; makeReview(p,'proposal','我收到修改后的提案了。请确认这份提交内容，后续会据此展开剧本。（原型使用固定示例剧本。）',{snapshot:p.proposal}); maybeDelegated(p); commitRender({bottom:true}); break;
    case 'review-view': {
      const r=p.messages.find(m=>m.review?.id===id)?.review; if(!r) break;
      if(r.snapshot!==undefined) modal(reviewName(p,r),`<p>以下为这轮审核绑定的提交内容。编辑器里之后的手改不会改变这份快照。</p><pre style="font:13px/1.9 var(--serif);white-space:pre-wrap;overflow-wrap:anywhere">${esc(r.snapshot)}</pre>${p.pending?.id===id?`<div class="dialog-footer"><button class="button primary" data-action="approve" data-id="${id}">确认并继续</button></div>`:''}`);
      else if(reviewAsset(r)==='video' && (r.versionId||r.baseId)) openAsset('video',r.versionId||r.baseId);
      else if(reviewAsset(r)==='visual') openAsset('visual');
      else modal('本次修改意见',`<p>${esc(r.text)}</p><p>${esc(r.feedback || '')}</p>${(r.refs||[]).map(a=>`<p>${clockTime(a.time)} · 第 ${version(p,a.versionId)?.number} 版<br>${esc(a.text)}</p>`).join('')}`);
      break;
    }
    case 'approve': if(dialog.open) closeModal(); approve(p,id); commitRender({bottom:true}); break;
    case 'play': {
      const t=p.tabs.find(t=>t.key===p.activeTab); if(t?.kind!=='video') break;
      if(playing) pause(); else { if(p.playheads[t.id]>=100) p.playheads[t.id]=0; playing=true; playbackVersion=t.id; lastFrame=performance.now(); if(!muted) sound.start().catch(()=>notice('浏览器未能开启声音，可以继续查看画面。')); }
      button.innerHTML=icon(playing?'pause':'play'); button.setAttribute('aria-label',playing?'暂停示例':'播放示例'); button.title=playing?'暂停示例':'播放示例'; break;
    }
    case 'mute': muted=!muted; if(muted) sound.stop(); else if(playing) sound.start().catch(()=>notice('浏览器未能开启声音。')); button.innerHTML=icon(muted?'mute':'volume'); button.setAttribute('aria-label',muted?'开启示例环境声':'关闭示例环境声'); button.title=muted?'开启示例环境声':'关闭示例环境声'; if(!muted) notice('开启合成环境低鸣；此原型不演示真实配乐。'); break;
    case 'fullscreen': document.querySelector('#player')?.requestFullscreen?.().catch(()=>notice('当前浏览器不支持全屏，可在作品侧栏预览。')); break;
    case 'annotate': {
      const t=p.tabs.find(t=>t.key===p.activeTab); if(t?.kind!=='video') break;
      pause(); const time=p.playheads[t.id]||0;
      modal(`标注 ${clockTime(time)} · 第 ${version(p,t.id).number} 版`,`<p>加入输入框后，你可以继续添加标注，再一起发给导演。</p><textarea class="dialog-textarea" id="annotation-text" aria-label="此处的修改意见" placeholder="例如：让音乐更晚进入，保留呼吸声。"></textarea><div class="dialog-footer"><button class="button primary" data-action="annotation-add" data-version="${t.id}" data-time="${time}">加入输入框 ${icon('arrow')}</button></div>`); document.querySelector('#annotation-text').focus(); break;
    }
    case 'annotation-add': {
      const text=document.querySelector('#annotation-text').value.trim(); if(!text) { document.querySelector('#annotation-text').focus(); break; }
      p.annotations.push({id:uid(),versionId:button.dataset.version,time:Number(button.dataset.time),text}); closeModal(); commitRender(); notice('标注已放入输入框，尚未发送。'); break;
    }
    case 'annotation-jump': { const a=p.annotations.find(a=>a.id===id); p.playheads[a.versionId]=a.time; openAsset('video',a.versionId); break; }
    case 'annotation-remove': p.annotations=p.annotations.filter(a=>a.id!==id); commitRender(); break;
    case 'annotation-send': send(id); break;
    case 'history': history(); break;
    case 'version-continue': {
      const v=version(p,id); if(!v) break; backupDraft(p);
      const cancelled=Boolean(p.task); p.task=null; p.pausedTask=null; p.pending=null; p.adoptedId=id; p.draftScript=v.script; p.appliedScript=v.script; p.stage=v.title==='试拍'?'trial':'finished';
      p.messages.push(director(`现在从第 ${v.number} 版继续。已有版本保留了，未提交的手改稿可以在剧本中找回。${cancelled?'刚才的示例制作也已结束，避免它覆盖这次选择。':''}`));
      if(v.title==='试拍') makeReview(p,'trial','已回到这份试拍。要沿这个方向完成影片时，请确认继续；也可以先给修改意见。',{versionId:v.id});
      touch(p); commitRender({bottom:true}); break;
    }
    case 'backups': modal('保留的手改稿',`<p>恢复只把文字放回编辑器；提交和应用仍由你决定。</p>${p.draftBackups.map((b,i)=>`<button class="history-row" data-action="library-open" data-kind="backup" data-id="${b.id}"><span><strong>手改稿 ${i+1}</strong><small>${new Date(b.created).toLocaleString('zh-CN')}</small></span>${icon('right')}</button>`).join('')}`); break;
    case 'backup-restore': { const b=p.draftBackups.find(b=>b.id===id); backupDraft(p); p.draftScript=b.text; openAsset('script'); notice('手改稿已回到编辑器，尚未提交。'); break; }
    case 'stop': requestStop(p); commitRender({bottom:true}); break;
    case 'demo-menu': modal('体验这个原型',`<p>所有项目、导演回复、连接检查和制作进展均为示例。状态保存在本浏览器；关闭页面后没有真实任务在后台运行。无需真实 API Key。</p><button class="asset-row" data-action="demo-from-menu"><span><strong>打开《最后一束光》</strong><small>查看作品，试试标注和版本操作</small></span>${icon('right')}</button>${p?`<button class="asset-row" data-action="simulate-failure"><span><strong>演示制作异常</strong><small>用导演的普通文字说明问题，再回复“继续”</small></span>${icon('right')}</button>`:''}<p style="margin:20px 0 0">原型用于讨论创作体验，不代表影片能力已经实现。示例画面采用原创程序绘制，未使用参考电影素材。</p>`); break;
    case 'demo-from-menu': closeModal(); state.activeId=state.projects.find(x=>x.title==='最后一束光')?.id||state.projects[0]?.id; commitRender({bottom:true}); break;
    case 'simulate-failure': closeModal(); p.pausedTask=p.task||p.pausedTask; p.task=null; p.stage='failed'; p.messages.push(director('这一轮示例制作暂时受阻：模拟的视频服务没有返回结果。已经完成的作品和你的草稿都保留着。建议稍后重试；你回复“继续”，我会从已有版本继续演示。')); commitRender({bottom:true}); break;
    case 'dialog-close': closeModal(); break;
  }
});

document.addEventListener('input',event=>{
  const p=pNow(), target=event.target;
  if(target.id==='composer-input') { if(p) p.composer=target.value; else state.welcomeDraft=target.value; persist(); }
  if(target.id==='script-editor'&&p) { p.draftScript=target.value; const ok=save(state); document.querySelector('#save-status').textContent=ok?(p.draftScript===p.appliedScript?'已保存 · 当前制作稿':'已保存 · 有修改未提交'):'未能保存 · 请下载草稿保留'; }
  if(target.dataset.annotationInput&&p) { const a=p.annotations.find(a=>a.id===target.dataset.annotationInput); if(a) a.text=target.value; persist(); }
  if(target.id==='seek'&&p) {
    const tab=p.tabs.find(t=>t.key===p.activeTab); p.playheads[tab.id]=Number(target.value);
    document.querySelector('#play-time').textContent=clockTime(Number(target.value)); drawFilm(document.querySelector('#film-canvas'),Number(target.value),version(p,tab.id)?.treatment); persist();
  }
});
document.addEventListener('keydown',event=>{
  if(event.isComposing) return;
  if(event.target.id==='composer-input'&&event.key==='Enter'&&!event.shiftKey) { event.preventDefault(); send(); }
});
dialog.addEventListener('click',e=>{ if(e.target===dialog) { const r=dialog.getBoundingClientRect(); if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom) closeModal(); } });

setInterval(()=>{
  let changed=false;
  for(const p of state.projects) if(p.task&&Date.now()>=p.task.due) { finishTask(p); changed=true; }
  if(changed) commitRender({bottom:true});
},250);

function frame(now) {
  const delta=Math.min((now-lastFrame)/1000,.2); lastFrame=now;
  const p=pNow(); const tab=p?.tabs.find(t=>t.key===p.activeTab);
  if(playing&&p?.workOpen&&tab?.kind==='video'&&tab.id===playbackVersion) {
    p.playheads[tab.id]=Math.min(100,(p.playheads[tab.id]||0)+delta);
    drawFilm(document.querySelector('#film-canvas'),p.playheads[tab.id],version(p,tab.id)?.treatment);
    const seek=document.querySelector('#seek'); if(seek) seek.value=p.playheads[tab.id];
    const label=document.querySelector('#play-time'); if(label) label.textContent=clockTime(p.playheads[tab.id]);
    if(p.playheads[tab.id]>=100) { pause(); const b=document.querySelector('[data-action="play"]'); b.innerHTML=icon('play'); b.setAttribute('aria-label','播放示例'); }
    if(now-lastStored>1000) { persist(); lastStored=now; }
  }
  requestAnimationFrame(frame);
}
// Reload restores sample state, but never pretends work ran while the page was closed.
for(const p of state.projects) {
  if(p.task) { const stopping=p.task.status==='stopping'; p.pausedTask=p.task; p.task=null; p.stage='stopped'; p.messages.push(director(stopping?'页面重新打开，示例已停止。之前的停止请求与已有内容均已保留。':'页面重新打开，已恢复示例项目。上次的页面计时演示已停止；回复“继续”可以继续体验。真实后台任务恢复仍需后续实现。')); }
}
persist(); render({bottom:true}); requestAnimationFrame(frame);
