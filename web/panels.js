import {esc,markdown,date,kinds,button} from './workspace.js';

const assetGroups=[['all','全部'],['documents','文稿'],['images','图片'],['shots','视频镜头'],['sounds','声音'],['films','预演、成片与母版']];
function assetGroup(a){
 if(a.kind==='image')return 'images';
 if(a.kind==='video')return 'shots';
 if(['audio','native_mixed'].includes(a.kind))return 'sounds';
 if(['film','trial','animatic','picture_master'].includes(a.kind))return 'films';
 return 'documents';
}
export function libraryAssets(snapshot,filters={}){
 const query=(filters.query||'').trim().toLowerCase();
 return [...snapshot.artifacts].reverse().filter(a=>(!filters.group||filters.group==='all'||assetGroup(a)===filters.group)&&
  (!query||(a.title+' '+(kinds[a.kind]||a.kind)+' '+a.id).toLowerCase().includes(query)));
}
export function mediaTaskSummary(snapshot){
 const counts={active:0,failed:0,completed:0};
 for(const job of snapshot.jobs){
  if(['pending','submitting','queued','running','downloading','rendering'].includes(job.status))counts.active++;
  if(['failed','unknown','download_failed','query_failed'].includes(job.status))counts.failed++;
  if(job.status==='succeeded')counts.completed++;
 }
 return `媒体任务 · ${counts.active?`进行中 ${counts.active} · `:''}已完成 ${counts.completed}${counts.failed?` · 受阻记录 ${counts.failed}`:''}`;
}
export function libraryPanel(snapshot,filters={}){
 const assets=libraryAssets(snapshot,filters),total=snapshot.artifacts.length;
 return `<section class="asset-library" aria-label="当前对话资产库"><header class="asset-library-heading"><div class="asset-library-eyebrow">当前对话 · ${esc(snapshot.project.title)}</div><h1>资产库 <span>${total}</span></h1><p>这里保存这段对话的文稿、素材与成片，包括中间产物和历史版本。</p></header><div class="asset-library-controls"><input id="asset-search" type="search" aria-label="搜索当前对话资产" placeholder="搜索名称、类型或资产 ID…" value="${esc(filters.query||'')}"><div class="asset-group-filters" aria-label="资产分类">${assetGroups.map(([group,label])=>{const count=group==='all'?total:snapshot.artifacts.filter(a=>assetGroup(a)===group).length;return button('library-filter',`${label} <span>${count}</span>`,`data-id="${group}" aria-pressed="${(filters.group||'all')===group}"`);}).join('')}</div></div>${snapshot.jobs.length?`<button class="library-task-link" data-action="activity" data-id="media">${esc(mediaTaskSummary(snapshot))}<span>查看运行记录 ↗</span></button>`:''}<div class="library-result-count">${filters.query||filters.group&&filters.group!=='all'?`${assets.length} / ${total}`:total} 项资产 · 最新在前</div><div id="asset-library-results">${assets.map(a=>{
 const adopted=snapshot.project.adopted[a.kind]===a.id,pending=snapshot.reviews.some(r=>r.artifact_id===a.id&&r.status==='pending');
 const group=assetGroup(a),glyph={documents:'文',images:'图',shots:'▶',sounds:'♫',films:'▶'}[group];
 const media=a.meta?.media,details=[kinds[a.kind]||a.kind,date(a.created)];
 if(a.kind!=='image'&&Number.isFinite(media?.duration)&&media.duration>0)details.push(media.duration.toFixed(1)+' 秒');
 const dimensions=media?.streams?.find(s=>s.width&&s.height)||media;
 if(dimensions?.width&&dimensions?.height)details.push(`${dimensions.width} × ${dimensions.height}`);
 return `<button class="library-asset" data-action="asset" data-id="${a.id}"><span class="library-asset-preview ${group}">${a.kind==='image'?`<img src="/api/media/${a.id}" alt="" loading="lazy">`:`<span aria-hidden="true">${glyph}</span>`}</span><span class="library-asset-info"><strong>${esc(a.title)}</strong><small>${details.map(esc).join(' · ')}</small><span class="library-asset-state ${adopted?'adopted':''}">${adopted?'当前采用':pending?'待审核':'保留版本'}</span></span><span class="library-open" aria-hidden="true">↗</span></button>`;
 }).join('')||`<div class="library-empty"><strong>${total?'没有匹配的资产':'还没有生成资产'}</strong><p>${total?'试试其他名称或分类。':'继续和导演聊创意，生成的文稿和素材会自动收录到这里。'}</p></div>`}</div></section>`;
}
export function conversationAssets(snapshot){
 const recent=snapshot.artifacts.filter(a=>!['picture_master','continuity_check'].includes(a.kind)).slice(-3);
 if(!snapshot.artifacts.length)return '';
 return `<section class="conversation-assets" aria-label="最近产物"><div class="conversation-assets-heading"><span>最近产物</span>${button('library',`打开资产库 · ${snapshot.artifacts.length} 项`)}</div><div class="artifact-links">${recent.map(a=>`<button class="artifact-link" data-action="asset" data-id="${a.id}" title="${esc(a.title)}"><span>${esc(a.title)}</span><span aria-hidden="true">↗</span></button>`).join('')}</div></section>`;
}
export function reviewPanel(r){return r?`<section class="review"><div class="review-label">需要你的审核 · ${esc(kinds[r.kind]||'作品')}</div><div class="prose">${markdown(r.question)}</div><div class="runtime-actions">${button('asset','查看审核内容',`data-id="${r.artifact_id}"`)}${button('approve','确认并继续',`data-id="${r.id}"`)}${button('reject','提出修改',`data-id="${r.id}"`)}</div><small>只确认这份作品；有意见也可以直接在对话中提出。</small></section>`:'';}
export function draftLabel(project,edit,saving){if(edit?.conflict)return '保存冲突 · 你的修改已保留';if(edit?.dirty)return saving?'正在保存…':'有未保存修改';return project.draft.revision>0?(project.draft.submitted_revision===project.draft.revision?'已保存 · 已提交导演':'已保存 · 有修改未提交'):'独立草稿 · 编辑后自动保存';}
export function draftPanel(project,edit,saving,artifact){const source=artifact(edit?.source??project.draft.source_artifact_id);return `<div class="script-pane"><div class="script-toolbar"><span class="save-state" id="save-state">${draftLabel(project,edit,saving)}</span>${button('save-script','保存草稿')}${button('submit-script','提交修改')}</div><div class="draft-context">${source?'起稿依据：'+esc(source.title):'当前项目的独立草稿'} · 保存不会改变影片</div><textarea id="script-editor" class="script-editor" aria-label="剧本编辑器" spellcheck="false">${esc(edit?.text??project.draft.text)}</textarea><div class="artifact-footnote">提交后导演会理解你的改动，再按当前授权提出方案。${edit?.conflict?button('copy-draft','复制保留我的修改'):''}</div></div>`;}
function sourceIds(a){
 const m=a.meta||{},entries=m.manifest?.entries||[];
 return new Set([...Object.values(m.basis||{}),m.parent,m.brief_id,m.manifest_id,m.shot_input_id,m.source_artifact_id,m.edit?.brief_id,...(m.edit?.clips||[]).map(c=>c.artifact_id),...(m.edit?.tracks||[]).map(t=>t.artifact_id),
  ...(m.asset_ids||[]),...(m.references||[]).map(r=>r.artifact_id),
  ...entries.flatMap(e=>[e.artifact_id,...(e.parent_asset_ids||[]),...(e.evidence_ids||[])])].filter(Boolean));
}
export function artifactRelations(a,snapshot){
 const ids=sourceIds(a),sources=snapshot.artifacts.filter(x=>ids.has(x.id)),uses=snapshot.artifacts.filter(x=>x.id!==a.id&&sourceIds(x).has(a.id));
 const production=['production_brief','reference_manifest','shot_input','animatic'].includes(a.kind);
 const stale=production&&(a.meta?.candidate_only||Object.entries(a.meta?.basis||{}).some(([kind,id])=>snapshot.project.adopted[kind]!==id));
 const links=items=>items.map(x=>button('asset',esc(x.title),`data-id="${esc(x.id)}"`)).join('');
 return (stale?'<p class="version-hint">这份制作依据已过时或尚未采用，内容仍保留；新制作需先核对当前版本。</p>':'')+
  (sources.length||uses.length?`<details class="media-sources" data-detail="relations-${esc(a.id)}"><summary>制作来源与使用记录</summary>${sources.length?`<p>依据与素材</p>${links(sources)}`:''}${uses.length?`<p>引用这份版本的作品</p>${links(uses)}`:''}</details>`:'');
}
export function artifactPanel(a,snapshot,artifact){
 const adopted=snapshot.project.adopted[a.kind]===a.id,r=snapshot.reviews.find(r=>r.artifact_id===a.id&&r.status==='pending');
 const head=`<div class="artifact-meta"><span>${esc(kinds[a.kind]||a.kind)} · ${date(a.created)}</span><span class="version-badge ${adopted?'adopted':''}">${adopted?'当前采用':r?'待审核版本':'保留版本'}</span></div><h1>${esc(a.title)}</h1>${artifactRelations(a,snapshot)}`;
 const download=`<a class="button" href="/api/artifacts/${a.id}/download" download>下载${['film','trial','animatic','video','picture_master','image','audio','native_mixed'].includes(a.kind)?'原文件':'文稿'}</a>`;
 if(['film','trial','animatic','video','picture_master'].includes(a.kind))return `<div class="document">${head}${a.kind==='animatic'||a.meta.previsualization?'<p class="version-hint">分镜预演 · 静态画面与临时声音。用于检查事件顺序与节奏，真实运动、表演与声音效果仍需后续试拍和人评。</p>':''}<video id="film-player" data-artifact="${a.id}" class="runtime-video" src="/api/media/${a.id}" controls preload="metadata">${a.meta.vtt_path?`<track kind="subtitles" src="/api/artifacts/${a.id}/subtitles" srclang="zh" label="中文字幕" default>`:''}</video><div class="runtime-actions">${a.kind!=='picture_master'?button('annotate','标注当前时间点'):''}${download}${a.meta.subtitle_path?`<a class="button" href="/api/artifacts/${a.id}/subtitles?format=srt" download>字幕</a>`:''}${button('history','版本记录')}${['film','trial'].includes(a.kind)&&!adopted?button('adopt','从此版本继续',`data-id="${a.id}"`):''}</div><small>${a.meta.media?.duration?.toFixed(1)||'—'} 秒 · ${a.meta.picture_master_id?'已保留独立画面母版':'生成源或派生文件'} · ${esc(a.id.slice(0,8))}</small>${reviewPanel(r)}${a.meta.edit?`<details data-detail="sources-${a.id}" class="media-sources"><summary>使用的镜头与声音</summary>${[...(a.meta.edit.clips||[]),...(a.meta.edit.tracks||[])].map(c=>button('asset',esc(artifact(c.artifact_id)?.title||c.artifact_id.slice(0,8)),`data-id="${c.artifact_id}"`)).join('')}</details>`:''}</div>`;
 if(a.kind==='image')return `<div class="document">${head}<img class="runtime-image" src="/api/media/${a.id}" alt="${esc(a.title)}">${download}</div>`;
 if(['audio','native_mixed'].includes(a.kind))return `<div class="document">${head}<audio id="audio-player" data-artifact="${a.id}" controls src="/api/media/${a.id}"></audio><div class="runtime-actions">${download}</div></div>`;
 return `<div class="document">${head}${a.kind==='script'?`<div class="document-actions">${button('edit-draft','编辑草稿',`data-id="${a.id}"`)}${button('history','版本记录')}${download}</div><p class="version-hint">正在阅读这份版本的原文。手改在独立的“剧本草稿”标签中保存。</p>`:''}${(a.meta.asset_ids||[]).map(id=>artifact(id)?.kind==='image'?`<button data-action="asset" data-id="${id}"><img class="runtime-image" src="/api/media/${id}" alt="${esc(artifact(id).title)}"></button>`:'').join('')}<div class="prose document-prose">${markdown(a.text)}</div>${reviewPanel(r)}${a.kind!=='script'?download:''}</div>`;
}
export function libraryRows(snapshot,query,kind,historyKind){return [...snapshot.artifacts].reverse().filter(a=>(!kind||a.kind===kind)&&(!historyKind||a.kind===historyKind)&&(a.title+' '+a.id).toLowerCase().includes(query.toLowerCase())).map(a=>`<button class="asset-row" data-action="asset" data-id="${a.id}">${a.kind==='image'?`<img src="/api/media/${a.id}" alt="" loading="lazy">`:''}<span><strong>${esc(a.title)}</strong><small>${esc(kinds[a.kind]||a.kind)} · ${date(a.created)}${snapshot.project.adopted[a.kind]===a.id?' · 当前采用':''}</small></span><span>↗</span></button>`).join('')||'<p class="empty-artifact">没有匹配的作品。</p>';}
