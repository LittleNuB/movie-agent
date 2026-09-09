import { openSettings } from './settings.js';
import { esc, button, time, markdown, date, roles, kinds, statuses, modeNames, trace, jobRows, workStatus, activityRows } from './workspace.js';
import { reviewPanel, draftLabel, draftPanel, artifactPanel, libraryRows, libraryPanel, conversationAssets, mediaTaskSummary } from './panels.js';

const $ = selector => document.querySelector(selector);
export {esc};
export const icon = name => name==='logo'
  ? '<svg class="brand-glyph" viewBox="0 0 64 64" aria-hidden="true"><use href="/logo.svg#reveal"/></svg>'
  : `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${({plus:'M12 5v14M5 12h14',close:'m6 6 12 12M18 6 6 18',panel:'M4 4h16v16H4zM9 4v16',work:'M4 4h16v16H4zM15 4v16',arrow:'M12 19V5m-6 6 6-6 6 6',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3M12 19v3M2 12h3M19 12h3',film:'M4 5h16v14H4zM8 5v14M16 5v14',sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v2M12 20v2M2 12h2M20 12h2',stop:'M6 6h12v12H6z',history:'M3 4v5h5M3 9a9 9 0 1 1 1 8M12 7v6l4 2',note:'M4 4h16v12H9l-5 4zM8 8h8M8 12h5',eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z'})[name] || 'M6 3h8l4 4v14H6zM9 12h6M9 16h6'}"/></svg>`;
const ib = (action, name, label) => `<button class="icon-button" data-action="${action}" aria-label="${label}" title="${label}">${icon(name)}</button>`;
export async function api(path, method='GET', body) {
  let response;
  try{response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});}catch{throw Error('无法连接本地服务，请确认服务正在运行');}
  const data = await response.json();
  if(!response.ok){const error=Error(data.error||'请求失败');error.status=response.status;throw error;}
  return data;
}
export function notice(text) { const box=$('#notice'); box.textContent=text; box.classList.add('visible'); clearTimeout(notice.timer); notice.timer=setTimeout(()=>box.classList.remove('visible'),6000); }
export function modal(title, body, wide=false) { const d=$('#dialog'); d.className=wide?'api-dialog':''; d.innerHTML=`<div class="dialog-heading"><h2 id="dialog-title">${esc(title)}</h2>${ib('close-modal','close','关闭')}</div><div class="dialog-body">${body}</div>`; if(!d.open)d.showModal(); }

let projects=[], snapshot=null, activeId=null, composer='', newMode='co', navOpen=true;
const requestedProject=new URLSearchParams(location.search).get('project');
if(requestedProject&&/^[a-f0-9]{32}$/.test(requestedProject))activeId=requestedProject;
let refreshTimer, loading=0, composing=false;
const views=new Map(), draftEdits=new Map();
const saving=new Map(), pendingSends=new Map();
let autosaveTimer, sending=false;
let projectQuery='', libraryQuery='', libraryKind='', libraryHistory=false, connection='connecting', sendError='';
const composers=new Map();
let activitySection='runs';
const mediaPositions=new Map(), readingPositions=new Map();
let panelWidth=48;
try{panelWidth=Number(localStorage.getItem('movie-agent.runtime.panel-width'))||48;navOpen=localStorage.getItem('movie-agent.runtime.nav')!=='false';}catch{}
function keepView(){if(activeId)try{localStorage.setItem('movie-agent.runtime.view.'+activeId,JSON.stringify(view()));}catch{}}
function keepComposer(){if($('#message-input')){composer=$('#message-input').value;composers.set(activeId||'new',composer);try{sessionStorage.setItem('movie-agent.runtime.composer.'+(activeId||'new'),composer);}catch{}}}
function restoreComposer(){try{composer=composers.get(activeId||'new')??sessionStorage.getItem('movie-agent.runtime.composer.'+(activeId||'new'))??'';}catch{composer='';}}
restoreComposer();
let theme=localStorage.getItem('movie-agent.runtime.theme')||'system';
function setTheme(){document.documentElement.dataset.theme=theme==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):theme;}
setTheme();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',setTheme);
function view(){if(!views.has(activeId)){let saved;try{saved=JSON.parse(localStorage.getItem('movie-agent.runtime.view.'+activeId));}catch{}views.set(activeId,saved||{open:false,tabs:[],tab:null,seen:false});}const v=views.get(activeId);v.tabs=['library',...new Set((v.tabs||[]).filter(id=>id!=='library'))];v.tab??='library';v.library??={query:'',group:'all'};return v;}
const artifact = id => snapshot?.artifacts.find(a=>a.id===id);
const pendingAnnotations = () => snapshot?.annotations.filter(a=>!a.submitted_message_id&&!a.removed)||[];

async function refresh(){
  const id=activeId, ticket=++loading;
  const [list,data]=await Promise.all([api('/projects'),id?api('/projects/'+id):Promise.resolve(null)]);
  if(ticket!==loading||id!==activeId)return;
  if(data&&snapshot?.project.id===id)for(const m of data.messages){const old=snapshot.messages.find(x=>x.id===m.id);if(m.streaming&&old?.text.length>m.text.length)m.text=old.text;}
  projects=list;snapshot=data;
  if(connection==='sync_error')connection='connected';
  if(data){const v=view();if(!v.seen&&data.artifacts.length){const preferred=data.reviews.find(r=>r.status==='pending')?.artifact_id||data.project.adopted.film||data.project.adopted.trial||data.project.adopted.script;const first=data.artifacts.find(a=>a.id===preferred)||data.artifacts.findLast(a=>a.kind!=='picture_master');if(first){v.open=true;v.tab=first.id;v.tabs=[first.id];v.seen=true;}}}
  render();
}
function scheduleRefresh(){if(refreshTimer)return;refreshTimer=setTimeout(()=>{refreshTimer=null;refresh().catch(()=>{connection='sync_error';updateConnection();setTimeout(scheduleRefresh,3000);});},250);}
function updateConnection(){const e=$('#connection-state');if(!e)return;e.className='connection-state '+connection;e.textContent=({connected:'本地服务已连接',connecting:'连接本地服务…',sync_error:'作品状态暂未同步 · 正在重试',disconnected:'连接已断开 · 正在重连'})[connection];}
async function selectProject(id){keepComposer();activeId=id;snapshot=null;restoreComposer();if($('#message-input'))$('#message-input').value=composer;history.replaceState(null,'',id?'?project='+id:location.pathname);sendError='';await refresh();}
function openArtifact(id){if(!['draft','library'].includes(id)&&!artifact(id))return;const v=view();v.open=true;v.seen=true;if(!v.tabs.includes(id))v.tabs.push(id);v.tab=id;keepView();render();}

function renderMessage(m){
 if(m.role==='user'){
  const entry=(snapshot.inputs||[]).find(i=>i.id==='input-'+m.id), labels={pending:'已接收 · 等待处理',processing:'已接收 · 处理中',done:'已处理',failed:'处理受阻'};
  return `<article class="message user"><div class="user-bubble">${(m.annotation_ids||[]).map(id=>{const a=snapshot.annotations.find(x=>x.id===id);return a?`<button class="sent-ref" data-action="seek" data-id="${a.artifact_id}" data-time="${a.time}">${time(a.time)} · ${esc(artifact(a.artifact_id)?.title)}<br>${esc(a.text)}</button>`:'';}).join('')}${esc(m.text)}</div><small class="message-meta">${date(m.created)}${entry?' · '+(labels[entry.status]||'已发送'):''}</small></article>`;
 }
 const run=snapshot.runs.find(r=>r.id===m.run_id||r.message_id===m.id),received=run?(snapshot.inputs||[]).filter(i=>i.run_id===run.id&&i.source==='user'):[];
 return `<article class="message director"><div class="director-byline"><span class="director-avatar">${icon('logo')}</span>主导演${m.error?'<span class="error-label">处理受阻</span>':''}</div>${run?trace(snapshot,run.id):''}${received.length>1?`<small class="message-meta">本轮已接收 ${received.length} 条消息，包含你的补充</small>`:''}<div class="message-text prose ${m.streaming?'streaming':''}" id="message-${m.id}">${m.text?markdown(m.text):m.streaming?'<span class="thinking-label">正在处理你的想法…</span>':''}</div>${!m.streaming&&m.text?`<div class="message-actions">${button('copy-message','复制回复',`data-id="${m.id}"`)}<small>${date(m.created)}</small></div>`:''}</article>`;
}
function renderWork(){
 const v=view(),a=artifact(v.tab);
 const tabs=v.tabs.filter(id=>['draft','library'].includes(id)||artifact(id));
 const labels={library:'资产库',draft:'剧本草稿'};
 return `<div class="pane-resizer" role="separator" aria-orientation="vertical" tabindex="0" aria-label="调整作品侧栏宽度"></div><aside class="work-pane" aria-label="作品侧栏"><div class="work-header"><div>${button('library','资产库')}${button('draft','剧本草稿')}</div>${ib('close-work','close','收起作品侧栏')}</div><div class="tabs" role="tablist">${tabs.map(id=>`<div class="tab ${id===v.tab?'active':''} ${id==='library'?'pinned-tab':''}"><button role="tab" aria-selected="${id===v.tab}" data-action="${id==='library'?'library':id==='draft'?'draft':'asset'}" data-id="${id}">${esc(labels[id]||artifact(id).title)}</button>${id==='library'?'':`<button class="icon-button" data-action="close-tab" data-id="${id}" aria-label="关闭标签">${icon('close')}</button>`}</div>`).join('')}</div><div class="artifact-body">${v.tab==='library'?libraryPanel(snapshot,v.library):v.tab==='draft'?draftPanel(snapshot.project,draftEdits.get(activeId),saving.has(activeId),artifact):a?artifactPanel(a,snapshot,artifact):'<div class="empty-artifact">从资产库打开剧本、图片或影片。</div>'}</div></aside>`;
}
function renderComposer(p, busy){
 const state=workStatus(snapshot);
 const activeMedia=snapshot?.jobs.some(j=>['pending','submitting','queued','running','rendering','downloading'].includes(j.status));
 return `<div class="composer-zone">${p?`<div class="working-status" data-state="${state.tone}" role="status"><span class="activity-dot ${state.tone==='running'?'pulse':''}"></span><span class="working-summary">${esc(state.text)}</span>${button('activity','查看过程')}</div>`:''}${sendError?`<p class="send-error" role="alert">${esc(sendError)} · 输入已保留，可再次发送。</p>`:''}<div class="composer">${pendingAnnotations().map(a=>`<div class="annotation-draft"><button class="annotation-ref" data-action="seek" data-id="${a.artifact_id}" data-time="${a.time}">${time(a.time)} · ${esc(artifact(a.artifact_id)?.title)}</button><span>${esc(a.text)}</span><div class="annotation-actions">${button('send-annotation','单条发送',`data-id="${a.id}"`)}${button('edit-annotation','编辑',`data-id="${a.id}"`)}${button('remove-annotation','移除',`data-id="${a.id}"`)}</div></div>`).join('')}<textarea id="message-input" aria-label="给导演发消息" placeholder="${p?'继续聊聊，或告诉导演你想怎么改…':'你想拍一个怎样的故事？一句话、一个画面，都可以。'}" rows="2">${esc(composer)}</textarea><div class="composer-bottom"><button class="mode-trigger" data-action="mode">${modeNames[p?.mode||newMode]} <span>⌄</span></button><div class="composer-actions">${p?.production_paused?button('resume','继续制作'):''}${p&&(busy||(!p.production_paused&&activeMedia))?ib('stop','stop','中止当前制作'):''}<button class="send-button" data-action="send" aria-label="发送消息" ${sending?'disabled':''}>${icon('arrow')}</button></div></div></div><div class="composer-help">${p?.production_paused?'媒体制作已暂停，发送讨论消息不会自动恢复。':busy?'可以继续发送补充，导演会接收。':'Enter 发送 · Shift + Enter 换行'}${pendingAnnotations().length?' · 发送时一并提交 '+pendingAnnotations().length+' 条标注':''}</div></div>`;
}
function renderWelcome(composerHTML){
 return `<section class="welcome" aria-label="开始电影创作"><div class="welcome-inner"><div class="welcome-heading"><div class="welcome-orbit"><div class="brand-mark">${icon('logo')}</div></div><h1>让一个想法，成为一段电影。</h1><p>从故事、人物或一个画面开始，导演陪你把它拍出来。</p></div>${composerHTML}<div class="starter-prompts" aria-label="创作灵感">${['先一起想一个有趣的故事','我有一个画面，想把它拍出来','帮我梳理故事，先不生成素材'].map(t=>button('starter',esc(t),`data-text="${esc(t)}"`)).join('')}</div></div></section>`;
}
function render(){
 if(composing)return;
 const media=[...document.querySelectorAll('video[data-artifact],audio[data-artifact]')];
 for(const old of media)mediaPositions.set(old.dataset.artifact,old.currentTime);
 const oldBody=$('.artifact-body');if(oldBody?.dataset.reading)readingPositions.set(oldBody.dataset.reading,oldBody.scrollTop);
 const focused=document.activeElement,focusId=focused?.id,selection=focused&&'selectionStart' in focused?[focused.selectionStart,focused.selectionEnd]:null;
 const focusAction=focused?.dataset.action,focusArtifact=focused?.dataset.id,focusRole=focused?.getAttribute('role'),focusSeparator=focused?.classList.contains('pane-resizer');
 const c=$('#conversation'),scroll=c?.scrollTop||0,nearBottom=!c||c.scrollHeight-scroll-c.clientHeight<100;
 const opened=new Set([...document.querySelectorAll('details[open][data-detail]')].map(d=>d.dataset.detail));
 keepComposer();const p=snapshot?.project,v=activeId?view():null,busy=snapshot?.runs.some(r=>['running','pending'].includes(r.status));
 const composerHTML=renderComposer(p,busy);
 $('#app').innerHTML=`<div class="shell ${v?.open?'with-work':''} ${navOpen?'':'nav-closed'}" style="--work-width:${panelWidth}%"><aside class="sidebar"><div class="brand"><div class="brand-mark">${icon('logo')}</div><strong>Movie Agent</strong>${ib('nav','panel','展开或收起项目侧栏')}</div><button class="new-project" data-action="new">${icon('plus')}<span>新建影片</span><kbd>Ctrl K</kbd></button><div class="project-search"><input id="project-search" aria-label="搜索影片" placeholder="搜索影片…" value="${esc(projectQuery)}"></div><div class="sidebar-content"><div class="section-label">影片项目</div>${projects.filter(x=>x.title.toLowerCase().includes(projectQuery.toLowerCase())).map(x=>`<button class="project-item ${x.id===p?.id?'active':''}" data-action="project" data-id="${x.id}"><strong>${esc(x.title)}</strong><small><i class="status-dot ${x.status==='running'?'pulse':''}"></i>${esc(statuses[x.status]||x.status)}</small></button>`).join('')||'<small class="empty-projects">影片会保存在这里</small>'}</div><div class="sidebar-bottom"><button class="text-button" data-action="settings">${icon('settings')}<span class="hide-collapsed">模型设置</span></button><button class="text-button" data-action="theme">${icon('sun')}<span class="hide-collapsed">外观 · ${theme==='system'?'跟随系统':theme==='dark'?'夜间':'日间'}</span></button><small class="connection-state ${connection}" id="connection-state">${connection==='connected'?'本地服务已连接':connection==='connecting'?'连接本地服务…':'连接已断开 · 正在重连'}</small></div></aside><main class="chat-pane ${p?'':'is-welcome'}"><header class="chat-header"><div class="header-leading"><div class="title-group"><button class="project-title" data-action="${p?'rename':'noop'}">${esc(p?.title||'新影片')}${p?'<span class="rename-hint">⌄</span>':''}</button><span class="eyebrow">${p?esc(modeNames[p.mode])+' · '+(p.production_paused?'媒体制作暂停':'本地电影项目'):'从想法开始，慢慢拍出来'}</span></div></div><div class="header-actions">${p?button('library','资产库')+button('activity','运行记录')+ib('work','work','打开作品侧栏'):''}</div></header>${p?`<div class="conversation" id="conversation"><div class="chat-body">${snapshot.messages.map(renderMessage).join('')}${conversationAssets(snapshot)}${snapshot.reviews.filter(r=>r.status==='pending').map(reviewPanel).join('')}${snapshot.jobs.length?`<button class="conversation-task-link" data-action="activity" data-id="media">${esc(mediaTaskSummary(snapshot))}<span>查看任务 ↗</span></button>`:''}</div></div><button class="jump-latest" data-action="latest" ${nearBottom?'hidden':''}>↓ 回到最新消息</button>${composerHTML}`:renderWelcome(composerHTML)}</main>${v?.open?renderWork():''}</div>`;
 for(const old of media){const fresh=document.querySelector(`[data-artifact="${old.dataset.artifact}"]`);if(fresh&&fresh.tagName===old.tagName)fresh.replaceWith(old);}
 for(const fresh of document.querySelectorAll('video[data-artifact],audio[data-artifact]'))if(!media.includes(fresh)&&mediaPositions.has(fresh.dataset.artifact)){const position=mediaPositions.get(fresh.dataset.artifact);fresh.addEventListener('loadedmetadata',()=>{fresh.currentTime=position;},{once:true});}
 for(const d of document.querySelectorAll('details[data-detail]'))if(opened.has(d.dataset.detail))d.open=true;
 if($('#conversation'))$('#conversation').scrollTop=nearBottom?$('#conversation').scrollHeight:scroll;
 if($('.artifact-body')){const body=$('.artifact-body');body.dataset.reading=activeId+':'+v.tab;body.scrollTop=readingPositions.get(body.dataset.reading)||0;}
 if(focusId&&document.getElementById(focusId)){const el=document.getElementById(focusId);el.focus({preventScroll:true});if(selection?.[0]!==null&&selection&&el.setSelectionRange)el.setSelectionRange(...selection);}
 else if(focusSeparator)$('.pane-resizer')?.focus({preventScroll:true});
 else if(focusAction&&focusArtifact)document.querySelector(`${focusRole?`[role="${CSS.escape(focusRole)}"]`:''}[data-action="${CSS.escape(focusAction)}"][data-id="${CSS.escape(focusArtifact)}"]`)?.focus({preventScroll:true});
 resizeComposer();
 updateConnection();
 if($('#dialog').open&&$('#activity-content'))updateActivity();
}
function resizeComposer(){const e=$('#message-input');if(e){e.style.height='auto';e.style.height=Math.min(180,Math.max(56,e.scrollHeight))+'px';}if($('.jump-latest'))$('.jump-latest').style.bottom=($('.composer-zone').offsetHeight+8)+'px';}

async function saveScript(){
  clearTimeout(autosaveTimer);
  if(saving.has(activeId)){const waiting=activeId;await saving.get(waiting);if(waiting!==activeId)return;return saveScript();}
  const pid=activeId,p=snapshot.project,text=draftEdits.get(pid)?.text??p.draft.text;
  const edit=draftEdits.get(pid);
  if(edit?.conflict)throw Error('草稿发生版本冲突，当前手改内容已保留在编辑器中，请先复制保留并核对版本。');
  if(text===p.draft.text){if(edit)draftEdits.set(pid,{...edit,dirty:false,base:p.draft.revision});return p.draft;}
  const request=api(`/projects/${pid}/draft`,'PUT',{text,expected_revision:edit?.base??p.draft.revision,source_artifact_id:edit?.source??p.draft.source_artifact_id});saving.set(pid,request);
  try{const saved=await request;const latest=draftEdits.get(pid);const newer=latest&&latest.text!==text;const currentText=newer?latest.text:text;if(activeId===pid)snapshot.project.draft=saved;draftEdits.set(pid,{text:currentText,base:saved.revision,source:saved.source_artifact_id,dirty:!!newer});if(activeId===pid&&$('#save-state'))$('#save-state').textContent=draftLabel(snapshot.project,draftEdits.get(pid),false);if(newer&&activeId===pid)autosaveTimer=setTimeout(()=>saveScript().catch(e=>notice(e.message)),500);return saved;}
  catch(e){const latest=draftEdits.get(pid);draftEdits.set(pid,{...latest,text:latest?.text??text,base:edit?.base??p.draft.revision,dirty:true,conflict:e.status===409});if(activeId===pid){render();if($('#save-state'))$('#save-state').textContent=e.status===409?'保存冲突 · 你的修改已保留':'保存失败 · 修改仍在编辑器，可重试';}throw e;}
  finally{saving.delete(pid);}
}
async function send(annotationId){
  if(sending)return;
  const text=$('#message-input')?.value.trim()||'', annotations=annotationId?[annotationId]:pendingAnnotations().map(a=>a.id);
  if(!text&&!annotations.length)return;
  sending=true;sendError='';let pid=activeId,delivered=false;
  try{
  if(!pid){const p=await api('/projects','POST',{mode:newMode});pid=p.id;composers.set(pid,text);composers.delete('new');sessionStorage.removeItem('movie-agent.runtime.composer.new');if(!activeId){activeId=pid;history.replaceState(null,'','?project='+activeId);}}
  const signature=JSON.stringify([pid,text,annotations]);if(!pendingSends.has(signature))pendingSends.set(signature,crypto.randomUUID());
  await api(`/projects/${pid}/messages`,'POST',{text,annotation_ids:annotations,client_id:pendingSends.get(signature)});
  delivered=true;
  pendingSends.delete(signature);
  if(activeId===pid&&$('#message-input')?.value.trim()===text){composer='';$('#message-input').value='';keepComposer();}else if((composers.get(pid)||'').trim()===text){composers.set(pid,'');sessionStorage.removeItem('movie-agent.runtime.composer.'+pid);}
  await refresh();
  }catch(e){if(delivered){notice('消息已送达，界面刷新暂时失败，恢复连接后会同步。');scheduleRefresh();}else if(activeId===pid){sendError=e.message;render();throw e;}else notice('原影片的消息未能送达，输入已保留，请返回该影片重试。');}finally{sending=false;const b=$('[data-action="send"]');if(b)b.disabled=false;}
}

document.addEventListener('input',e=>{
  if(e.target.id==='script-editor'){const prior=draftEdits.get(activeId);draftEdits.set(activeId,{...prior,text:e.target.value,base:prior?.base??snapshot.project.draft.revision,source:prior?.source??snapshot.project.draft.source_artifact_id,dirty:true});$('#save-state').textContent='有未保存修改';clearTimeout(autosaveTimer);autosaveTimer=setTimeout(()=>saveScript().catch(err=>notice(err.message)),800);}
  if(e.target.id==='message-input'){keepComposer();resizeComposer();}
  if(e.target.id==='project-search'){projectQuery=e.target.value;render();}
  if(e.target.id==='asset-search'){view().library.query=e.target.value;keepView();render();}
  if(e.target.id==='library-search'||e.target.id==='library-kind'){libraryQuery=$('#library-search').value;libraryKind=$('#library-kind').value;$('#library-results').innerHTML=libraryRows(snapshot,libraryQuery,libraryKind,libraryHistory);}
});
document.addEventListener('compositionstart',e=>{if(['script-editor','message-input','project-search','asset-search'].includes(e.target.id))composing=true;});
document.addEventListener('compositionend',()=>{composing=false;scheduleRefresh();});
window.addEventListener('resize',resizeComposer);
document.addEventListener('keydown',e=>{if(e.target.id==='message-input'&&e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();send().catch(err=>notice(err.message));}});
document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-action]');if(!b||b.disabled)return;
  const id=b.dataset.id,action=b.dataset.action;
  try{
    if(action==='close-modal'){$('#dialog').close();return;}
    if(action==='settings'){await openSettings();return;}
    if(action==='new'){if(draftEdits.get(activeId)?.dirty)await saveScript();await selectProject(null);return;}
    if(action==='project'){if(draftEdits.get(activeId)?.dirty)await saveScript();await selectProject(id);return;}
    if(action==='send'||action==='send-annotation'){b.disabled=true;await send(action==='send-annotation'?id:null);return;}
    if(action==='theme'){modal('外观',['system','light','dark'].map(t=>button('set-theme',t==='system'?'跟随系统':t==='light'?'日间':'夜间',`data-id="${t}" aria-pressed="${theme===t}"`)).join(''));return;}
    if(action==='set-theme'){theme=id;localStorage.setItem('movie-agent.runtime.theme',theme);setTheme();$('#dialog').close();render();return;}
    if(action==='nav'){navOpen=!navOpen;localStorage.setItem('movie-agent.runtime.nav',navOpen);render();return;}
    if(action==='work'){view().open=true;keepView();render();if(!view().tabs.length)showLibrary();return;}
    if(action==='close-work'){view().open=false;view().seen=true;keepView();render();return;}
    if(action==='asset'){$('#dialog').close();openArtifact(id);return;}
    if(action==='close-tab'){if(id==='library')return;view().tabs=view().tabs.filter(x=>x!==id);if(view().tab===id)view().tab=view().tabs.at(-1);keepView();render();return;}
    if(action==='starter'){$('#message-input').value=b.dataset.text;keepComposer();resizeComposer();$('#message-input').focus();return;}
    if(action==='activity'){showActivity(id==='media'?'media':'runs');return;}
    if(action==='activity-section'){activitySection=id;updateActivity();return;}
    if(action==='library-filter'){view().library.group=id;keepView();render();return;}
    if(action==='latest'){$('#conversation').scrollTo({top:$('#conversation').scrollHeight,behavior:'smooth'});return;}
    if(action==='copy-message'){await navigator.clipboard.writeText(snapshot.messages.find(m=>m.id===id).text);notice('回复已复制');return;}
    if(action==='copy-draft'){await navigator.clipboard.writeText(draftEdits.get(activeId)?.text??snapshot.project.draft.text);notice('你的修改已复制');return;}
    if(action==='rename'){modal('影片名称',`<input id="project-title-input" class="dialog-textarea" aria-label="影片名称" maxlength="200" value="${esc(snapshot.project.title)}"><div class="dialog-footer">${button('save-title','保存名称')}</div>`);return;}
    if(action==='save-title'){await api(`/projects/${activeId}/title`,'PUT',{title:$('#project-title-input').value});$('#dialog').close();await refresh();return;}
    if(action==='draft'||action==='edit-draft'){if(action==='edit-draft'&&!snapshot.project.draft.revision&&!draftEdits.has(activeId)){draftEdits.set(activeId,{text:artifact(id).text,base:0,source:id,dirty:true});}openArtifact('draft');if(draftEdits.get(activeId)?.dirty)await saveScript();return;}
    if(action==='seek'){openArtifact(id);const player=$('#film-player');if(player){const seek=()=>{player.currentTime=Number(b.dataset.time);player.pause();};if(player.readyState)seek();else player.addEventListener('loadedmetadata',seek,{once:true});}return;}
    if(action==='library'){showLibrary();return;}
    if(action==='history'){showLibrary(true);return;}
    if(action==='save-script'){await saveScript();return;}
    if(action==='submit-script'){const pid=activeId;clearTimeout(autosaveTimer);let saved=await saveScript();while(activeId===pid&&draftEdits.get(pid)?.dirty)saved=await saveScript();if(activeId!==pid)throw Error('已切换影片，草稿已保留，请回到原影片提交。');await api(`/projects/${pid}/draft/submit`,'POST',{expected_revision:saved.revision});notice('已提交剧本，导演将先理解并给出修改方案。');await refresh();return;}
    if(action==='approve'){b.disabled=true;await api(`/projects/${activeId}/reviews/${id}`,'POST',{approve:true});await refresh();return;}
    if(action==='reject'){modal('提出修改',`<textarea class="dialog-textarea" id="review-feedback" placeholder="告诉导演你想怎样调整"></textarea><div class="dialog-footer">${button('send-review-feedback','发送修改意见',`data-id="${id}"`)}</div>`);return;}
    if(action==='send-review-feedback'){await api(`/projects/${activeId}/reviews/${id}`,'POST',{approve:false,feedback:$('#review-feedback').value});$('#dialog').close();await refresh();return;}
    if(action==='stop'){b.disabled=true;const result=await api(`/projects/${activeId}/stop`,'POST',{});notice(result.message);await refresh();return;}
    if(action==='resume'){await api(`/projects/${activeId}/resume`,'POST',{});await refresh();return;}
    if(action==='mode'){modal('创作方式',Object.entries(modeNames).map(([m,label])=>`<label class="option"><input type="radio" name="mode" value="${m}" ${m===(snapshot?.project.mode||newMode)?'checked':''}><span><strong>${label}</strong><small>${m==='auto'?'授权导演推进创作与制作，仍可随时插话和中止。':'关键产物由你审核，修改先讨论再执行。'}</small></span></label>`).join('')+`<div class="dialog-footer">${button('save-mode','应用方式')}</div>`);return;}
    if(action==='save-mode'){const mode=$('input[name="mode"]:checked').value;if(activeId)await api(`/projects/${activeId}/mode`,'PUT',{mode});else newMode=mode;$('#dialog').close();await refresh();return;}
    if(action==='annotate'){const player=$('#film-player');player.pause();modal(`标注 ${time(player.currentTime)}`,`<textarea class="dialog-textarea" id="annotation-text" placeholder="这里想怎样调整？"></textarea><div class="dialog-footer">${button('save-annotation','加入对话框',`data-time="${player.currentTime}" data-id="${player.dataset.artifact}"`)}</div>`);return;}
    if(action==='save-annotation'){await api(`/projects/${activeId}/annotations`,'POST',{artifact_id:id,time:Number(b.dataset.time),text:$('#annotation-text').value});$('#dialog').close();await refresh();return;}
    if(action==='remove-annotation'){await api(`/projects/${activeId}/annotations/${id}`,'DELETE',{});await refresh();return;}
    if(action==='edit-annotation'){const a=snapshot.annotations.find(x=>x.id===id);modal('编辑标注',`<textarea id="annotation-text" class="dialog-textarea">${esc(a.text)}</textarea><div class="dialog-footer">${button('update-annotation','保存',`data-id="${id}"`)}</div>`);return;}
    if(action==='update-annotation'){const a=snapshot.annotations.find(x=>x.id===id);await api(`/projects/${activeId}/annotations/${id}`,'PUT',{artifact_id:a.artifact_id,time:a.time,text:$('#annotation-text').value});$('#dialog').close();await refresh();return;}
    if(action==='adopt'){const a=artifact(id);await api(`/projects/${activeId}/adopt`,'POST',{artifact_id:id,expected:snapshot.project.adopted[a.kind]||null});notice('已采用此版本，手改草稿与其他版本均已保留。');await refresh();return;}
    if(action==='recover'){const j=snapshot.jobs.find(j=>j.id===id);if(j.external_id||j.result){await api(`/projects/${activeId}/jobs/${id}/recover`,'POST',{});await refresh();}else modal('核对外部任务',`<p>提交结果不明时不会自动重发。请在服务商任务记录中核对对应输入，再填入该任务 ID。</p><input id="external-task-id" class="dialog-textarea" aria-label="外部任务 ID"><div class="dialog-footer">${button('bind-job','查询并恢复',`data-id="${id}"`)}</div>`);return;}
    if(action==='bind-job'){await api(`/projects/${activeId}/jobs/${id}/recover`,'POST',{external_id:$('#external-task-id').value.trim()});$('#dialog').close();await refresh();}
  }catch(err){notice(err.message);}finally{if(b.isConnected)b.disabled=false;}
});
function showLibrary(history=false){if(!history){openArtifact('library');return;}libraryHistory=history?(artifact(view().tab)?.kind||'film'):false;libraryQuery='';libraryKind='';modal(history?'版本记录':'全部作品',`<div class="library-controls"><input id="library-search" aria-label="搜索作品" placeholder="搜索作品名称…"><select id="library-kind" aria-label="作品类型"><option value="">全部类型</option>${Object.entries(kinds).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></div><div id="library-results">${libraryRows(snapshot,libraryQuery,libraryKind,libraryHistory)}</div>`,true);}
function showActivity(section='runs'){activitySection=section;modal('运行记录','<div id="activity-content"></div>',true);updateActivity();}
function updateActivity(){
 const s=snapshot,box=$('#activity-content');if(!s||!box)return;
 const focused=document.activeElement,focus=box.contains(focused)&&focused.dataset.action?{action:focused.dataset.action,id:focused.dataset.id}:null;
 const scroll=$('#dialog').scrollTop,closed=new Set([...box.querySelectorAll('details:not([open])')].map(d=>d.dataset.run));
 const tabs=`<div class="activity-sections">${button('activity-section','执行过程',`data-id="runs" aria-pressed="${activitySection==='runs'}"`)}${button('activity-section',`媒体任务 · ${s.jobs.length}`,`data-id="media" aria-pressed="${activitySection==='media'}"`)}</div>`;
 const runs=s.runs.slice().reverse().map(r=>`<details class="run-block" data-run="${r.id}" ${closed.has(r.id)?'':'open'}><summary>${esc(roles[r.role]||r.role)} · ${esc(statuses[r.status]||r.status)} · ${date(r.created)}</summary>${r.task?`<p>${esc(r.task)}</p>`:''}${activityRows((s.activities||[]).filter(a=>a.run_id===r.id))||'<small>该次运行没有更详细的活动记录。</small>'}<small>累计调用用量：输入 ${r.input_tokens||0} / 输出 ${r.output_tokens||0} tokens；非当前上下文占用。</small></details>`).join('');
 box.innerHTML=tabs+`<p>${esc(activitySection==='media'?mediaTaskSummary(s):workSummary(s))}</p><p class="activity-explanation">实际模型请求、工具与媒体任务记录，随运行更新。工具提交结束后，云端生成可能仍在运行。</p>`+(activitySection==='media'?(jobRows({...s,jobs:s.jobs.slice().reverse()})||'<p>还没有媒体任务。</p>'):(runs||'<p>发送消息后，执行记录会出现在这里。</p>'));
 $('#dialog').scrollTop=scroll;
 if(focus)box.querySelector(`[data-action="${CSS.escape(focus.action)}"]${focus.id?`[data-id="${CSS.escape(focus.id)}"]`:''}`)?.focus({preventScroll:true});
}
document.addEventListener('keydown',e=>{if(e.isComposing||$('#dialog').open)return;if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('[data-action="new"]').click();}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'&&$('#script-editor')){e.preventDefault();saveScript().catch(err=>notice(err.message));}if(e.target.classList.contains('pane-resizer')&&['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();panelWidth=Math.min(65,Math.max(32,panelWidth+(e.key==='ArrowLeft'?2:-2)));localStorage.setItem('movie-agent.runtime.panel-width',panelWidth);render();}});
document.addEventListener('scroll',e=>{if(e.target.id==='conversation'&&$('.jump-latest'))$('.jump-latest').hidden=e.target.scrollHeight-e.target.scrollTop-e.target.clientHeight<100;},true);
document.addEventListener('pointerdown',e=>{if(!e.target.classList.contains('pane-resizer'))return;e.preventDefault();const move=ev=>{panelWidth=Math.min(65,Math.max(32,(innerWidth-ev.clientX)/innerWidth*100));$('.shell').style.setProperty('--work-width',panelWidth+'%');};const end=()=>{localStorage.setItem('movie-agent.runtime.panel-width',panelWidth);document.removeEventListener('pointermove',move);document.removeEventListener('pointerup',end);};document.addEventListener('pointermove',move);document.addEventListener('pointerup',end);});
window.addEventListener('beforeunload',e=>{keepComposer();keepView();if([...draftEdits.values()].some(d=>d.dirty)){e.preventDefault();e.returnValue='';}});
const events=new EventSource('/api/events');
events.onopen=()=>{connection='connected';scheduleRefresh();};
events.onmessage=event=>{
 const data=JSON.parse(event.data);
 if(data.kind==='text_delta'&&data.project_id===activeId){const m=snapshot?.messages.find(m=>m.id===data.body.id),box=$('#message-'+data.body.id);if(m&&box){if(!m.streaming)return;const length=Array.from(m.text).length;if(data.body.offset<length)return;if(data.body.offset!==length){scheduleRefresh();return;}m.text+=data.body.delta;const c=$('#conversation'),bottom=c.scrollHeight-c.scrollTop-c.clientHeight<100;box.innerHTML=markdown(m.text);if(bottom)c.scrollTop=c.scrollHeight;return;}}
 scheduleRefresh();
};
events.onerror=()=>{connection='disconnected';const e=$('#connection-state');if(e){e.className='connection-state disconnected';e.textContent='连接已断开 · 正在重连';}};
await refresh().catch(e=>{connection='disconnected';render();notice(e.message);});
