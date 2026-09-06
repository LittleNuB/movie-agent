import { openSettings } from './settings.js';

const $ = selector => document.querySelector(selector);
export const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${({plus:'M12 5v14M5 12h14',close:'m6 6 12 12M18 6 6 18',logo:'M5 18V6l7 9 7-9v12',panel:'M4 4h16v16H4zM9 4v16',work:'M4 4h16v16H4zM15 4v16',arrow:'M12 19V5m-6 6 6-6 6 6',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3M12 19v3M2 12h3M19 12h3',film:'M4 5h16v14H4zM8 5v14M16 5v14',sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v2M12 20v2M2 12h2M20 12h2',stop:'M6 6h12v12H6z',history:'M3 4v5h5M3 9a9 9 0 1 1 1 8M12 7v6l4 2',note:'M4 4h16v12H9l-5 4zM8 8h8M8 12h5',eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z'})[name] || 'M6 3h8l4 4v14H6zM9 12h6M9 16h6'}"/></svg>`;
const button = (action, label, extra='') => `<button class="button" data-action="${action}" ${extra}>${label}</button>`;
const ib = (action, name, label) => `<button class="icon-button" data-action="${action}" aria-label="${label}" title="${label}">${icon(name)}</button>`;
export async function api(path, method='GET', body) {
  const response = await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
  const data = await response.json();
  if(!response.ok) throw Error(data.error || '请求失败');
  return data;
}
export function notice(text) { const box=$('#notice'); box.textContent=text; box.classList.add('visible'); clearTimeout(notice.timer); notice.timer=setTimeout(()=>box.classList.remove('visible'),6000); }
export function modal(title, body, wide=false) { const d=$('#dialog'); d.className=wide?'api-dialog':''; d.innerHTML=`<div class="dialog-heading"><h2 id="dialog-title">${esc(title)}</h2>${ib('close-modal','close','关闭')}</div><div class="dialog-body">${body}</div>`; if(!d.open)d.showModal(); }

const modeNames={co:'共创',auto:'托管',audio:'共创 · 声音托管'};
const kinds={proposal:'故事提案',script:'剧本',visual_plan:'视觉方案',shot_plan:'镜头计划',edit_plan:'修改方案',continuity_check:'媒体观察',image:'图片',video:'镜头',audio:'声音',trial:'试拍',film:'影片',picture_master:'画面母版'};
const statuses={idle:'等待你的想法',running:'导演处理中',waiting_review:'等你审核',stopped:'制作已中止',pending:'待执行',submitting:'正在提交',queued:'云端排队中',downloading:'保存素材中',rendering:'合成中',succeeded:'已完成',failed:'受阻',unknown:'提交结果待核对',cancelled_local:'本地已停止',download_failed:'结果已生成 · 下载受阻',query_failed:'云端状态查询受阻'};
let projects=[], snapshot=null, activeId=null, composer='', newMode='co', navOpen=true;
const requestedProject=new URLSearchParams(location.search).get('project');
if(requestedProject&&/^[a-f0-9]{32}$/.test(requestedProject))activeId=requestedProject;
let refreshTimer, loading=0, eventCursor=0;
const views=new Map(), draftEdits=new Map();
const saving=new Map(), pendingSends=new Map();
let autosaveTimer, sending=false;
let theme=localStorage.getItem('movie-agent.runtime.theme')||'system';
function setTheme(){document.documentElement.dataset.theme=theme==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):theme;}
setTheme();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',setTheme);
function view(){if(!views.has(activeId))views.set(activeId,{open:false,tabs:[],tab:null,seen:false});return views.get(activeId);}
const artifact = id => snapshot?.artifacts.find(a=>a.id===id);
const time = n => `${String(Math.floor(n/60)).padStart(2,'0')}:${String(Math.floor(n%60)).padStart(2,'0')}`;
const pendingAnnotations = () => snapshot?.annotations.filter(a=>!a.submitted_message_id&&!a.removed)||[];

async function refresh(){
  const id=activeId, ticket=++loading;
  const [list,data]=await Promise.all([api('/projects'),id?api('/projects/'+id):Promise.resolve(null)]);
  if(ticket!==loading||id!==activeId)return;
  projects=list;snapshot=data;
  if(data){const v=view();if(!v.seen&&data.artifacts.length){const first=data.artifacts.find(a=>a.kind!=='picture_master');if(first){v.open=true;v.tab=first.id;v.tabs=[first.id];v.seen=true;}}}
  render();
}
function scheduleRefresh(){clearTimeout(refreshTimer);refreshTimer=setTimeout(()=>refresh().catch(e=>notice(e.message)),450);}
async function selectProject(id){composer=$('#message-input')?.value||composer;activeId=id;snapshot=null;composer='';await refresh();}
function openArtifact(id){if(!artifact(id))return;const v=view();v.open=true;v.seen=true;if(!v.tabs.includes(id))v.tabs.push(id);v.tab=id;render();}

function renderMessage(m){
  if(m.role==='user')return `<article class="message user"><div class="user-bubble">${(m.annotation_ids||[]).map(id=>{const a=snapshot.annotations.find(x=>x.id===id);return a?`<div class="sent-ref">${time(a.time)} · ${esc(artifact(a.artifact_id)?.title)}<br>${esc(a.text)}</div>`:'';}).join('')}${esc(m.text)}</div></article>`;
  return `<article class="message director"><div class="director-byline"><span class="director-avatar">${icon('logo')}</span>导演</div><div class="message-text ${m.streaming?'streaming':''}" id="message-${m.id}">${esc(m.text)}</div></article>`;
}
function renderWork(){
  const v=view(), a=artifact(v.tab);
  return `<aside class="work-pane" aria-label="作品侧栏"><div class="work-header"><div>作品 ${button('library','全部作品')}</div>${ib('close-work','close','收起作品侧栏')}</div><div class="tabs" role="tablist">${v.tabs.filter(id=>artifact(id)).map(id=>`<div class="tab ${id===v.tab?'active':''}"><button role="tab" aria-selected="${id===v.tab}" data-action="asset" data-id="${id}">${esc(artifact(id).title)}</button><button class="icon-button" data-action="close-tab" data-id="${id}" aria-label="关闭标签">${icon('close')}</button></div>`).join('')}</div><div class="artifact-body">${a?renderArtifact(a):'<div class="document">从全部作品打开剧本、参考图或影片。</div>'}</div></aside>`;
}
function renderArtifact(a){
  const p=snapshot.project, review=snapshot.reviews.find(r=>r.artifact_id===a.id&&r.status==='pending');
  const toolbar=`<div class="runtime-status">${esc(kinds[a.kind])} · ${esc(a.id.slice(0,8))}${p.adopted[a.kind]===a.id?' · 当前采用':''}</div>`;
  const reviewBlock=review?`<div class="review"><p>${esc(review.question)}</p><div class="runtime-actions">${button('approve','确认并继续',`data-id="${review.id}"`)}${button('reject','提出修改',`data-id="${review.id}"`)}</div></div>`:'';
  const download=`<a class="button" href="/api/artifacts/${a.id}/download" download>下载</a>`;
  if(a.kind==='script'){
    const edit=draftEdits.get(p.id);const text=edit?.text??(p.draft.revision>0?p.draft.text:a.text);
    return `<div class="script-pane">${review?`<section class="script-review-snapshot"><h3>待审核版本：${esc(a.title)}</h3><pre class="runtime-document">${esc(a.text)}</pre>${reviewBlock}</section>`:''}<div class="script-toolbar"><span class="save-state" id="save-state">${edit?.dirty?'独立草稿 · 有未保存修改':p.draft.submitted_revision===p.draft.revision?'独立草稿 · 已提交':'独立草稿 · 保存与提交分开'}</span>${button('save-script','保存草稿')}${button('submit-script','提交修改')}</div><textarea id="script-editor" class="script-editor" aria-label="剧本编辑器">${esc(text)}</textarea><div class="artifact-footnote">${toolbar}你正在编辑独立草稿，保存不会应用到影片。${review?'上方审核仅对应完整展示的待审版本。':`<details><summary>查看打开版本的原文</summary><pre class="runtime-document">${esc(a.text)}</pre></details>`}</div></div>`;
  }
  if(['film','trial','video'].includes(a.kind))return `<div class="document">${toolbar}<h1>${esc(a.title)}</h1><video id="film-player" data-artifact="${a.id}" class="runtime-video" src="/api/media/${a.id}" controls preload="metadata">${a.meta.vtt_path?`<track kind="subtitles" src="/api/artifacts/${a.id}/subtitles" srclang="zh" label="中文字幕" default>`:""}</video><div class="runtime-actions">${button('annotate',icon('note')+'标注当前时间点')} ${download} ${a.meta.subtitle_path?`<a class="button" href="/api/artifacts/${a.id}/subtitles?format=srt" download>字幕文件</a>`:''} ${button('history','版本记录')}${button('adopt','从此版本继续',`data-id="${a.id}"`)}</div><div class="runtime-status">${a.meta.media?.duration?.toFixed(1)||'?'} 秒 · ${a.meta.picture_master_id?'保留独立画面母版':'生成源片段'}</div>${reviewBlock}${a.meta.edit?`<details><summary>采用素材与声音</summary><pre class="runtime-json">${esc(JSON.stringify(a.meta.edit,null,2))}</pre></details>`:''}</div>`;
  if(a.kind==='image')return `<div class="document">${toolbar}<h1>${esc(a.title)}</h1><img class="runtime-image" src="/api/media/${a.id}" alt="${esc(a.title)}">${download}</div>`;
  if(a.kind==='audio')return `<div class="document">${toolbar}<h1>${esc(a.title)}</h1><audio controls src="/api/media/${a.id}"></audio><div class="runtime-actions">${download}</div><p>此处播放实际保留的声音素材。</p></div>`;
  return `<div class="document">${toolbar}<h1>${esc(a.title)}</h1>${(a.meta.asset_ids||[]).map(id=>artifact(id)?.kind==='image'?`<button data-action="asset" data-id="${id}"><img class="runtime-image" src="/api/media/${id}" alt="${esc(artifact(id).title)}"></button>`:'').join('')}<div class="runtime-document">${esc(a.text)}</div>${reviewBlock}<div class="runtime-actions">${download}</div>${a.meta.shots?`<details><summary>镜头资料</summary><pre class="runtime-json">${esc(JSON.stringify(a.meta.shots,null,2))}</pre></details>`:''}</div>`;
}
function render(){
  const oldPlayer=$('#film-player'),oldAid=oldPlayer?.dataset.artifact;
  const focused=document.activeElement,focusId=focused?.id,selection=focused instanceof HTMLTextAreaElement?[focused.selectionStart,focused.selectionEnd]:null;
  const scroll=$('#conversation')?.scrollTop||0,nearBottom=!$('#conversation')||$('#conversation').scrollHeight-scroll-$('#conversation').clientHeight<120;
  if($('#message-input'))composer=$('#message-input').value;
  const p=snapshot?.project,v=activeId?view():null;
  $('#app').innerHTML=`<div class="shell ${v?.open?'with-work':''} ${navOpen?'':'nav-closed'}"><aside class="sidebar"><div class="brand"><div class="brand-mark">${icon('logo')}</div><strong>影片创作</strong></div><button class="new-project" data-action="new">${icon('plus')}<span>新建影片</span></button><div class="sidebar-content"><div class="section-label">我的影片</div>${projects.map(x=>`<button class="project-item ${x.id===p?.id?'active':''}" data-action="project" data-id="${x.id}"><strong>${esc(x.title)}</strong><small>${esc(statuses[x.status]||x.status)}</small></button>`).join('')}</div><div class="sidebar-bottom"><button class="text-button" data-action="settings">${icon('settings')}<span class="hide-collapsed">模型设置</span></button><button class="text-button" data-action="theme">${icon('sun')}<span class="hide-collapsed">日间 / 夜间</span></button><button class="text-button" data-action="nav">${icon('panel')}<span class="hide-collapsed">收起侧栏</span></button><span class="local-note hide-collapsed">本地运行 · API 生成</span></div></aside><main class="chat-pane"><header class="chat-header"><div class="title-group"><span class="project-title">${esc(p?.title||'新影片')}</span><span class="eyebrow">${p?esc(statuses[p.status]||p.status):'A STORY STARTS WITH YOU'}</span></div>${p?ib('work','work','打开作品侧栏'):''}</header>${p?`<div class="conversation" id="conversation"><div class="chat-body">${snapshot.messages.map(renderMessage).join('')}<div class="artifact-links">${snapshot.artifacts.filter(a=>!['picture_master','continuity_check'].includes(a.kind)).slice(-8).map(a=>`<button class="artifact-link" data-action="asset" data-id="${a.id}">${icon('film')}${esc(a.title)}</button>`).join('')}</div>${snapshot.reviews.filter(r=>r.status==='pending').map(r=>`<div class="review"><p>${esc(r.question)}</p><div class="runtime-actions">${button('asset','查看审核内容',`data-id="${r.artifact_id}"`)}${button('approve','确认并继续',`data-id="${r.id}"`)}${button('reject','提出修改',`data-id="${r.id}"`)}</div></div>`).join('')}${snapshot.jobs.length?`<details class="progress"><summary>制作进展 · ${snapshot.jobs.filter(j=>j.status==='succeeded').length}/${snapshot.jobs.length}</summary>${snapshot.jobs.map(j=>`<div class="runtime-task">${esc(j.title)} · ${esc(statuses[j.status]||j.status)}${j.candidate_only?' · 候选保留':''}<small>${esc(j.error||'')}</small>${['unknown','failed','download_failed','query_failed'].includes(j.status)?button('recover','核对与恢复',`data-id="${j.id}"`):''}</div>`).join('')}</details>`:''}</div></div>`:`<div class="welcome"><div class="welcome-inner"><div class="welcome-orbit"><div class="brand-mark">${icon('logo')}</div></div><div class="eyebrow">A STORY STARTS WITH YOU</div><h1>你想拍一个怎样的故事？</h1><p>一句话、一个画面，或一种感受都可以。<br>我们一起把它慢慢拍出来。</p><div class="welcome-actions">${button('settings','配置模型')}</div></div></div>`}<div class="composer-zone"><div class="composer">${pendingAnnotations().map(a=>`<div class="annotation-draft"><button class="annotation-ref" data-action="asset" data-id="${a.artifact_id}">${time(a.time)} · ${esc(artifact(a.artifact_id)?.title)}</button><span>${esc(a.text)}</span><div class="annotation-actions">${button('send-annotation','发送',`data-id="${a.id}"`)}${button('edit-annotation','编辑',`data-id="${a.id}"`)}${button('remove-annotation','移除',`data-id="${a.id}"`)}</div></div>`).join('')}<textarea id="message-input" aria-label="给导演发消息" placeholder="描述你的想法，或告诉我哪里想改…" rows="3">${esc(composer)}</textarea><div class="composer-bottom"><button class="mode-trigger" data-action="mode">${modeNames[p?.mode||newMode]}</button><div class="composer-actions">${p?.production_paused?button('resume','继续制作'):p?ib('stop','stop','中止当前制作'):''}<button class="send-button" data-action="send" aria-label="发送消息">${icon('arrow')}</button></div></div></div><div class="composer-help">${p?.production_paused?'制作已中止，仍可继续讨论。':'按 Enter 发送，Shift + Enter 换行。'}</div></div></main>${v?.open?renderWork():''}</div>`;
  const newPlayer=$('#film-player');if(oldPlayer&&newPlayer&&oldAid===newPlayer.dataset.artifact)newPlayer.replaceWith(oldPlayer);
  const player=$('#film-player');
  if(player&&artifact(player.dataset.artifact)?.meta.vtt_path&&!player.querySelector('track')){const captions=document.createElement('track');captions.kind='subtitles';captions.label='中文字幕';captions.srclang='zh';captions.src=`/api/artifacts/${player.dataset.artifact}/subtitles`;captions.default=true;player.append(captions);const link=document.createElement('a');link.className='button';link.textContent='下载字幕';link.href=`/api/artifacts/${player.dataset.artifact}/subtitles?format=srt`;link.download='subtitles.srt';player.parentElement.querySelector('.runtime-actions')?.append(link);}
  if($('#conversation'))$('#conversation').scrollTop=nearBottom?$('#conversation').scrollHeight:scroll;
  if(focusId&&$( '#'+focusId)&&selection){$('#'+focusId).focus({preventScroll:true});$('#'+focusId).setSelectionRange(...selection);}
}

async function saveScript(){
  clearTimeout(autosaveTimer);
  if(saving.has(activeId)){await saving.get(activeId);return saveScript();}
  const pid=activeId,p=snapshot.project,text=$('#script-editor')?.value??draftEdits.get(pid)?.text??p.draft.text;
  const edit=draftEdits.get(pid);
  if(edit?.conflict)throw Error('草稿发生版本冲突，当前手改内容已保留在编辑器中，请先复制保留并核对版本。');
  if(text===p.draft.text)return p.draft;
  const request=api(`/projects/${pid}/draft`,'PUT',{text,expected_revision:edit?.base??p.draft.revision,source_artifact_id:edit?.source??view().tab});saving.set(pid,request);
  try{const saved=await request;const latest=draftEdits.get(pid);const newer=latest&&latest.text!==text;const currentText=newer?latest.text:text;if(activeId===pid)snapshot.project.draft=saved;draftEdits.set(pid,{text:currentText,base:saved.revision,dirty:!!newer});if(activeId===pid&&$('#save-state'))$('#save-state').textContent=newer?'正在保存新修改…':'草稿已保存，尚未应用';if(newer&&activeId===pid)autosaveTimer=setTimeout(()=>saveScript().catch(e=>notice(e.message)),500);return saved;}
  catch(e){const latest=draftEdits.get(pid);draftEdits.set(pid,{text:latest?.text??text,base:edit?.base??p.draft.revision,dirty:true,conflict:true});throw e;}
  finally{saving.delete(pid);}
}
async function send(annotationId){
  if(sending)return;
  const text=$('#message-input')?.value.trim()||'', annotations=annotationId?[annotationId]:pendingAnnotations().map(a=>a.id);
  if(!text&&!annotations.length)return;
  sending=true;
  try{
  if(!activeId){const p=await api('/projects','POST',{mode:newMode});activeId=p.id;}
  const signature=JSON.stringify([activeId,text,annotations]);if(!pendingSends.has(signature))pendingSends.set(signature,crypto.randomUUID());
  await api(`/projects/${activeId}/messages`,'POST',{text,annotation_ids:annotations,client_id:pendingSends.get(signature)});
  pendingSends.delete(signature);
  composer='';if($('#message-input'))$('#message-input').value='';await refresh();
  }finally{sending=false;}
}

document.addEventListener('input',e=>{
  if(e.target.id==='script-editor'){const prior=draftEdits.get(activeId);draftEdits.set(activeId,{...prior,text:e.target.value,base:prior?.base??snapshot.project.draft.revision,source:prior?.source??view().tab,dirty:true});$('#save-state').textContent='有未保存修改';clearTimeout(autosaveTimer);autosaveTimer=setTimeout(()=>saveScript().catch(err=>notice(err.message)),800);}
});
document.addEventListener('keydown',e=>{if(e.target.id==='message-input'&&e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();send().catch(err=>notice(err.message));}});
document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-action]');if(!b||b.disabled)return;
  const id=b.dataset.id,action=b.dataset.action;
  try{
    if(action==='close-modal'){$('#dialog').close();return;}
    if(action==='settings'){await openSettings();return;}
    if(action==='new'){if(draftEdits.get(activeId)?.dirty)await saveScript();activeId=null;snapshot=null;composer='';render();return;}
    if(action==='project'){if(draftEdits.get(activeId)?.dirty)await saveScript();await selectProject(id);return;}
    if(action==='send'||action==='send-annotation'){b.disabled=true;await send(action==='send-annotation'?id:null);return;}
    if(action==='theme'){theme=document.documentElement.dataset.theme==='dark'?'light':'dark';localStorage.setItem('movie-agent.runtime.theme',theme);setTheme();return;}
    if(action==='nav'){navOpen=!navOpen;render();return;}
    if(action==='work'){view().open=true;render();if(!view().tabs.length)showLibrary();return;}
    if(action==='close-work'){view().open=false;view().seen=true;render();return;}
    if(action==='asset'){$('#dialog').close();openArtifact(id);return;}
    if(action==='close-tab'){view().tabs=view().tabs.filter(x=>x!==id);if(view().tab===id)view().tab=view().tabs.at(-1);render();return;}
    if(action==='library'){showLibrary();return;}
    if(action==='history'){showLibrary(true);return;}
    if(action==='save-script'){await saveScript();return;}
    if(action==='submit-script'){const pid=activeId;clearTimeout(autosaveTimer);let saved=await saveScript();while(activeId===pid&&draftEdits.get(pid)?.dirty)saved=await saveScript();if(activeId!==pid)throw Error('已切换影片，草稿已保留，请回到原影片提交。');await api(`/projects/${pid}/draft/submit`,'POST',{expected_revision:saved.revision});notice('已提交剧本，导演将先理解并给出修改方案。');await refresh();return;}
    if(action==='approve'){b.disabled=true;await api(`/projects/${activeId}/reviews/${id}`,'POST',{approve:true});await refresh();return;}
    if(action==='reject'){modal('提出修改',`<textarea class="dialog-textarea" id="review-feedback" placeholder="告诉导演你想怎样调整"></textarea><div class="dialog-footer">${button('send-review-feedback','发送修改意见',`data-id="${id}"`)}</div>`);return;}
    if(action==='send-review-feedback'){await api(`/projects/${activeId}/reviews/${id}`,'POST',{approve:false,feedback:$('#review-feedback').value});$('#dialog').close();await refresh();return;}
    if(action==='stop'){b.disabled=true;const result=await api(`/projects/${activeId}/stop`,'POST',{});notice(result.message);await refresh();return;}
    if(action==='resume'){await api(`/projects/${activeId}/resume`,'POST',{});await refresh();return;}
    if(action==='mode'){modal('创作方式',Object.entries(modeNames).map(([m,label])=>`<label class="option"><input type="radio" name="mode" value="${m}" ${m===(snapshot?.project.mode||newMode)?'checked':''}><span><strong>${label}</strong><small>${m==='auto'?'授权导演推进创作与制作，仍可随时插话和中止。':m==='audio'?'故事与视觉由你审核，声音由导演推进。':'关键产物由你审核，修改先讨论再执行。'}</small></span></label>`).join('')+`<div class="dialog-footer">${button('save-mode','应用方式')}</div>`);return;}
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
function showLibrary(history=false){modal(history?'影片版本':'全部作品',snapshot.artifacts.filter(a=>history?['film','trial'].includes(a.kind):a.kind!=='picture_master').slice().reverse().map(a=>`<button class="asset-row" data-action="asset" data-id="${a.id}"><span><strong>${esc(a.title)}</strong><small>${esc(kinds[a.kind])} · ${a.id.slice(0,8)}${snapshot.project.adopted[a.kind]===a.id?' · 当前采用':''}</small></span>${icon('film')}</button>`).join('')||'<p>作品会随着创作逐步出现。</p>');}
window.addEventListener('beforeunload',e=>{if([...draftEdits.values()].some(d=>d.dirty)){e.preventDefault();e.returnValue='';}});
const events=new EventSource('/api/events');
events.onmessage=event=>{
  eventCursor=Number(event.lastEventId);const data=JSON.parse(event.data);
  if(data.kind==='text_delta'&&data.project_id===activeId){const box=$('#message-'+data.body.id);if(box){box.textContent+=data.body.delta;return;}}
  scheduleRefresh();
};
events.onerror=()=>{if(eventCursor)notice('连接暂时中断，正在重连。已提交任务由本地服务继续管理。');};
await refresh();
