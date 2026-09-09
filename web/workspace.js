// Model-authored content is escaped before formatting; raw HTML is never rendered.
export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const kinds={proposal:'故事提案',script:'剧本',production_brief:'剧本制作说明',reference_manifest:'参考清单',shot_input:'镜头生成输入',animatic:'分镜预演',visual_plan:'视觉方案',shot_plan:'镜头计划',edit_plan:'修改方案',continuity_check:'媒体观察',image:'图片',video:'镜头',audio:'声音',native_mixed:'原生混音',trial:'试拍',film:'影片',picture_master:'画面母版'};
export const roles={director:'主导演',visual:'视觉制作',post:'后期',check:'连续性检查',visual_evidence:'画面观察'};
export const statuses={idle:'等待你的想法',running:'处理中',waiting_review:'等待审核',stopped:'制作已暂停',pending:'已接收 · 等待处理',processing:'已接收 · 处理中',done:'已处理',preparing:'准备调用',submitting:'提交中',queued:'云端排队',downloading:'保存素材',rendering:'本地合成',succeeded:'已完成',completed:'已完成',ended:'本轮已结束',failed:'受阻',unknown:'提交结果待核对',cancelled_local:'本地已停止',interrupted:'已中断',download_failed:'下载受阻',query_failed:'查询受阻'};
export const modeNames={co:'共创',auto:'托管'};
export const time=n=>`${String(Math.floor((n||0)/60)).padStart(2,'0')}:${String(Math.floor((n||0)%60)).padStart(2,'0')}`;
export const date=v=>v?new Date(v).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}):'';
export function markdown(text){
 const inline=s=>{
  let html='',end=0;
  for(const match of s.matchAll(/`([^`\n]+)`|\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*/g)){
   html+=esc(s.slice(end,match.index));
   html+=match[1]?`<code>${esc(match[1])}</code>`:match[2]?`<a href="${esc(match[3])}" target="_blank" rel="noopener noreferrer">${esc(match[2])}</a>`:match[4]?`<strong>${esc(match[4])}</strong>`:`<em>${esc(match[5])}</em>`;
   end=match.index+match[0].length;
  }
  return html+esc(s.slice(end));
 };
 const lines=String(text||'').split('\n'),cells=s=>s.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim());
 let code=false,list='',result='';
 const closeList=()=>{if(list){result+=`</${list}>`;list='';}};
 for(let i=0;i<lines.length;i++){
  const line=lines[i];
  if(line.startsWith('```')){closeList();result+=code?'</code></pre>':'<pre><code>';code=!code;continue;}
  if(code){result+=esc(line)+'\n';continue;}
  if(line.includes('|')&&lines[i+1]?.includes('-')&&cells(lines[i+1]).every(c=>/^:?-{3,}:?$/.test(c))){
   closeList();result+='<div class="table-scroll"><table><thead><tr>'+cells(line).map(c=>`<th>${inline(c)}</th>`).join('')+'</tr></thead><tbody>';i++;
   while(lines[i+1]?.includes('|')){i++;result+='<tr>'+cells(lines[i]).map(c=>`<td>${inline(c)}</td>`).join('')+'</tr>';}
   result+='</tbody></table></div>';continue;
  }
  const bullet=line.match(/^\s*(?:([-*])|(\d+)[.)、])\s+(.+)$/);
  if(bullet){const tag=bullet[2]?'ol':'ul';if(list!==tag){closeList();list=tag;result+=`<${tag}${tag==='ol'?` start="${Number(bullet[2])}"`:''}>`;}result+=`<li>${inline(bullet[3])}</li>`;continue;}
  closeList();
  const head=line.match(/^(#{1,6})\s+(.+)$/),quote=line.match(/^>\s?(.*)$/);
  result+=head?`<h3>${inline(head[2])}</h3>`:quote?`<blockquote>${inline(quote[1])}</blockquote>`:line.trim()?`<p>${inline(line)}</p>`:'<div class="paragraph-gap"></div>';
 }
 closeList();return result+(code?'</code></pre>':'');
}
export const button=(action,label,extra='')=>`<button class="button" data-action="${action}" ${extra}>${label}</button>`;
export const activityRows=items=>items.map(a=>`<div class="activity-row ${esc(a.status)}"><i class="activity-dot"></i><span>${esc(a.label||'执行活动')}<small>${esc(roles[a.role]||a.role||'')} · ${esc(statuses[a.status]||a.status)}${a.finished?' · '+date(a.finished):''}</small></span></div>`).join('');
export function trace(snapshot,runId){
 const items=(snapshot.activities||[]).filter(a=>a.run_id===runId);if(!items.length)return '';
 const running=items.findLast(a=>['preparing','running'].includes(a.status));
 return `<details class="trace" data-detail="trace-${runId}"><summary><span class="activity-dot ${running?'pulse':''}"></span><span class="trace-label">${esc(running?.label||'查看执行过程')}</span><small>${items.length} 项活动</small></summary><div class="trace-body">${activityRows(items)}</div></details>`;
}
export const jobRows=s=>s.jobs.map(j=>`<div class="job-row"><div><strong>${esc(j.title)}</strong><small>${esc(statuses[j.status]||j.status)}${j.candidate_only?' · 仅保留为候选':''} · ${date(j.created)}</small>${j.error?`<p>${esc(j.error)}</p>`:''}</div><div>${(j.artifact_ids||[]).map(id=>button('asset','查看结果',`data-id="${id}"`)).join('')}${['unknown','download_failed','query_failed'].includes(j.status)?button('recover','核对结果',`data-id="${j.id}"`):''}</div></div>`).join('');
export function workSummary(s){
 if(!s)return '先从一个想法开始';
 const p=s.project,pending=s.reviews.filter(r=>r.status==='pending').length,active=s.runs.filter(r=>['running','pending'].includes(r.status)),jobs=s.jobs.filter(j=>['pending','submitting','queued','running','rendering','downloading'].includes(j.status)),waiting=(s.inputs||[]).filter(i=>i.status==='pending').length;
 if(active.length){const a=(s.activities||[]).findLast(a=>['preparing','running'].includes(a.status));return a?`${roles[a.role]||'导演'} · ${a.label}`:`${roles[active[0].role]||'导演'}正在处理${waiting?' · 有新消息等待处理':''}`;}
 if(pending)return `有 ${pending} 项内容等你审核${p.production_paused?' · 媒体制作已暂停':''}`;
 if(p.production_paused)return '制作已暂停，可以继续讨论';
 if(jobs.length)return `${jobs.length} 项媒体任务进行中，仍可发送消息`;
 if(waiting)return '消息已接收，等待导演处理';
 if(s.runs.at(-1)?.status==='failed')return '上一轮处理受阻，可以继续说明或检查连接';
 return '这一轮已结束，随时继续';
}
