import { api, esc, icon, modal, notice } from './app.js';

let config, draft, key='', page='connections';
const caps={text:'对话',vision:'视觉理解',image:'图像生成',video:'视频生成',voice:'配音',music:'配乐',sfx:'音效'};
const names={director:'导演 / 对话',vision:'媒体视觉检查',image:'图像',video:'主用视频',videoFallback:'备选视频',voice:'配音',music:'配乐',sfx:'独立音效'};
const option=(value,label,selected)=>`<option value="${esc(value)}" ${value===selected?'selected':''}>${esc(label)}</option>`;
const field=(id,label,value,placeholder='',type='text')=>`<div class="api-field"><label for="${id}">${label}</label><input id="${id}" type="${type}" value="${esc(value)}" placeholder="${placeholder}" autocomplete="off"></div>`;
function select(id){draft=structuredClone(config.connections.find(c=>c.id===id)||{id:crypto.randomUUID(),name:'',protocol:'openai',base_url:'',no_key:false,models:[]});key='';}
function read(){if(!document.querySelector('#api-name'))return;draft.name=document.querySelector('#api-name').value.trim();draft.protocol=document.querySelector('#api-protocol').value;draft.base_url=document.querySelector('#api-url').value.trim();draft.no_key=document.querySelector('#api-no-key').checked;key=document.querySelector('#api-key').value;for(const row of document.querySelectorAll('[data-model-row]')){const model=draft.models.find(m=>m.uid===row.dataset.modelRow);for(const f of ['id','name','capability'])model[f]=row.querySelector(`[data-field="${f}"]`).value.trim();}}
function chrome(body){modal('模型与 API',`<nav class="settings-tabs"><button data-setting="connections" class="${page==='connections'?'active':''}">服务连接</button><button data-setting="assignments" class="${page==='assignments'?'active':''}">用途分配</button></nav>${body}<p class="runtime-config-note">Key 仅保存在此 Windows 用户的凭据管理器中。保存不调用模型；连接检查不生成媒体。</p>`,true);}
function renderConnections(){
  page='connections';
  chrome(`<div class="api-layout"><nav class="api-connections" aria-label="服务连接列表"><div class="api-list-heading">我的连接</div>${config.connections.map(c=>`<button class="api-connection ${c.id===draft.id?'selected':''}" data-setting="select" data-id="${c.id}"><strong>${esc(c.name)}</strong><small>${esc(config.protocols[c.protocol])} · ${c.models.length} 个模型</small></button>`).join('')}<button class="button api-add-connection" data-setting="new">${icon('plus')}添加连接</button>${config.connections.length?'':'<p class="api-list-empty">暂无连接，按服务商提供的 API 信息填写。</p>'}</nav><div class="api-editor"><div class="api-editor-title"><h3>${draft.name?esc(draft.name):'添加服务连接'}</h3><span class="pill">本地配置</span></div><div class="api-field-grid">${field('api-name','连接名称',draft.name,'我的模型服务')}<div class="api-field"><label for="api-protocol">接口类型</label><select id="api-protocol">${Object.entries(config.protocols).map(([id,label])=>option(id,label,draft.protocol)).join('')}</select></div></div>${field('api-url','API 地址 · Base URL',draft.base_url,'https://api.example.com/v1','url')}<div class="api-field"><label for="api-key">API Key</label><div class="api-key-field"><input id="api-key" type="password" autocomplete="new-password" placeholder="${draft.has_key?'已保存；留空保留，输入新 Key 可替换':'粘贴 API Key'}"><button class="icon-button" data-setting="show-key" aria-label="显示 API Key">${icon('eye')}</button></div><small>服务端不会向页面回读已有 Key。</small></div><label class="api-no-key"><input id="api-no-key" type="checkbox" ${draft.no_key?'checked':''}>此连接无需 API Key</label><div class="api-check-row"><button class="button" data-setting="check">检查已保存连接</button><button class="text-button" data-setting="discover">获取模型</button></div><p class="api-result" id="api-result" role="status">${draft.has_key?'凭据已保存在本机。':'请先保存连接。'}</p><div class="api-model-heading"><h3>模型</h3><small>模型 ID 由你填写，能力需实际验证。</small></div>${draft.models.map(m=>`<div class="api-model-row" data-model-row="${m.uid}"><div><input data-field="id" aria-label="模型 ID" placeholder="模型 ID" value="${esc(m.id)}"><input data-field="name" aria-label="显示名称" placeholder="显示名称（可选）" value="${esc(m.name)}"></div><select data-field="capability" aria-label="模型能力">${Object.entries(caps).map(([id,label])=>option(id,label,m.capability)).join('')}</select><button class="icon-button" data-setting="remove-model" data-id="${m.uid}" aria-label="移除模型">${icon('close')}</button></div>`).join('')}<button class="text-button" data-setting="add-model">${icon('plus')}手动添加模型</button><details><summary>高级模型参数</summary><p class="api-field-note">仅在服务商需要时填写 JSON，例如 reasoning_effort、thinking_enable、thinking 或 max_tokens；按模型 ID 区分。</p><textarea id="api-parameters" class="dialog-textarea" aria-label="高级模型参数">${esc(JSON.stringify(Object.fromEntries(draft.models.filter(m=>Object.keys(m.parameters||{}).length).map(m=>[m.id,m.parameters])),null,2))}</textarea></details><div class="api-editor-footer"><button class="text-button api-delete" data-setting="delete">删除连接</button><button class="button primary" data-setting="save">保存连接</button></div></div></div>`);
  document.querySelector('#api-key').value=key;
}
function renderAssignments(){page='assignments';chrome(`<div class="api-assignments"><p>可以先配置导演开始讨论，其他用途在制作需要时补充。产品不预设模型。</p>${Object.entries(names).map(([purpose,name])=>`<div class="api-purpose"><div><label for="purpose-${purpose}">${name}</label><small>${purpose==='vision'?'用于实际图片与视频抽帧检查':purpose==='sfx'?'未配置时使用生成视频的原生声音':''}</small></div><select id="purpose-${purpose}" data-purpose="${purpose}">${option('','未设置',config.assignments[purpose])}${config.connections.map(c=>`<optgroup label="${esc(c.name)}">${c.models.filter(m=>m.capability===config.purposes[purpose]).map(m=>option(c.id+'/'+m.uid,m.name||m.id,config.assignments[purpose])).join('')}</optgroup>`).join('')}</select></div>`).join('')}<div class="api-editor-footer"><button class="text-button" data-setting="connections">管理连接</button><button class="button primary" data-setting="save-assignments">保存用途分配</button></div></div>`);}
export async function openSettings(){config=await api('/config');select(config.connections[0]?.id);renderConnections();}
document.addEventListener('click',async event=>{
  const b=event.target.closest('[data-setting]');if(!b||b.disabled)return;
  const action=b.dataset.setting;
  try{
    if(page==='connections')read();
    if(action==='select'){select(b.dataset.id);renderConnections();return;}
    if(action==='new'){select();renderConnections();return;}
    if(action==='connections'){renderConnections();return;}
    if(action==='assignments'){renderAssignments();return;}
    if(action==='show-key'){const input=document.querySelector('#api-key');input.type=input.type==='password'?'text':'password';return;}
    if(action==='add-model'){draft.models.push({uid:crypto.randomUUID(),id:'',name:'',capability:'text',parameters:{}});renderConnections();return;}
    if(action==='remove-model'){draft.models=draft.models.filter(m=>m.uid!==b.dataset.id);renderConnections();return;}
    if(action==='save'){
      const parameters=JSON.parse(document.querySelector('#api-parameters').value||'{}');
      for(const m of draft.models)m.parameters=parameters[m.id]||{};
      b.disabled=true;config=await api('/connections','PUT',{...draft,api_key:key||undefined});select(draft.id);renderConnections();notice('连接已保存，没有调用模型。');return;
    }
    if(action==='save-assignments'){const assignments=Object.fromEntries([...document.querySelectorAll('[data-purpose]')].map(e=>[e.dataset.purpose,e.value]));config=await api('/assignments','PUT',assignments);notice('用途分配已保存。');return;}
    if(action==='delete'){if(!config.connections.some(c=>c.id===draft.id)){select();renderConnections();return;}config=await api('/connections/'+draft.id,'DELETE',{});select(config.connections[0]?.id);renderConnections();notice('已删除此连接及凭据，相关用途已清除。');return;}
    if(action==='check'||action==='discover'){
      const result=document.querySelector('#api-result');result.textContent='正在查询已保存的服务连接…';b.disabled=true;
      const reply=await api('/connections/'+draft.id+(action==='check'?'/check':'/models'),'POST',{});
      if(action==='discover'&&reply.models.length){const ids=reply.models.map(m=>m.id);result.textContent=reply.message+'。返回 '+ids.length+' 个模型。';let list=document.querySelector('#discovered-models');if(!list){list=document.createElement('select');list.id='discovered-models';list.className='dialog-textarea';result.after(list);}list.innerHTML=option('','选择模型以添加','')+ids.map(id=>option(id,id,'')).join('');list.onchange=()=>{if(!list.value)return;read();draft.models.push({uid:crypto.randomUUID(),id:list.value,name:'',capability:'text',parameters:{}});renderConnections();};}
      else result.textContent=reply.message;
    }
  }catch(e){notice(e.message);const result=document.querySelector('#api-result');if(result)result.textContent=e.message;}
  finally{if(b.isConnected)b.disabled=false;}
});
document.querySelector('#dialog').addEventListener('close',()=>{key='';const input=document.querySelector('#api-key');if(input)input.value='';});
