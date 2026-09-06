// Configuration UX only. No request is made, and credentials never enter state.
const capabilities = { text: '对话与推理', image: '图像生成', video: '视频生成', voice: '语音', music: '音乐', sfx: '音效' };
const purposes = [
  ['director','导演与对话','理解想法、编写剧本与组织创作','text'],
  ['image','图像生成','人物、场景与镜头参考图','image'],
  ['video','视频生成','试拍与影片中的动态片段','video'],
  ['videoFallback','备选视频模型','需要另一种效果时使用，可不设置','video'],
  ['voice','配音','角色对白与旁白，可稍后设置','voice'],
  ['music','配乐','音乐创作，可稍后设置','music'],
  ['sfx','音效','环境声与动作声音，可稍后设置','sfx'],
];

export function createModelSettings({ state, modal, persist, notice, esc, icon }) {
  state.modelSettings ||= { connections: [], assignments: {} };
  const config = state.modelSettings;
  const keys = new Map();
  let draft, screen = 'connections', requestGeneration = 0;
  const protocolName = p => p === 'openai' ? 'OpenAI 兼容' : '其他 / 专用接口';
  const newDraft = () => ({ id: crypto.randomUUID(), name:'', protocol:'openai', baseUrl:'', noKey:false, models:[] });
  const clone = value => JSON.parse(JSON.stringify(value));
  const option = (value,label,selected) => `<option value="${esc(value)}" ${selected===value?'selected':''}>${esc(label)}</option>`;
  const field = (id,label,input,hint='') => `<div class="api-field"><label for="${id}">${label}</label>${input}${hint?`<small>${hint}</small>`:''}</div>`;
  const input = (id,value,placeholder='',type='text') => `<input id="${id}" type="${type}" value="${esc(value)}" placeholder="${placeholder}" autocomplete="off" spellcheck="false">`;
  const selectDraft = id => { requestGeneration++; draft = clone(config.connections.find(c=>c.id===id) || newDraft()); };

  function chrome(body) {
    modal('模型与 API',`<p class="api-intro">连接你自己的模型服务，再选择创作时使用的模型。</p><div class="api-tabs" role="tablist" aria-label="模型设置分类"><button role="tab" aria-selected="${screen==='connections'}" data-api="connections">服务连接</button><button role="tab" aria-selected="${screen==='assignments'}" data-api="assignments">用途分配</button></div>${body}<p class="api-prototype-note">交互原型：检查与获取模型仅作演示，不发送 API 请求。API Key 仅暂存在当前页面内存，刷新后清除。</p>`);
    document.querySelector('#dialog').classList.add('model-settings-dialog');
  }
  function modelRows() {
    return draft.models.map(m=>`<div class="api-model-row" data-model="${m.uid}"><div><input data-model-field="id" aria-label="模型 ID" value="${esc(m.id)}" placeholder="服务商提供的模型 ID" autocomplete="off" spellcheck="false"><input data-model-field="name" aria-label="模型显示名称" value="${esc(m.name)}" placeholder="显示名称（可选）" autocomplete="off"></div><select data-model-field="capability" aria-label="模型能力">${option('','选择能力',m.capability)}${Object.entries(capabilities).map(([value,label])=>option(value,label,m.capability)).join('')}</select><button class="icon-button" data-api="remove-model" data-id="${m.uid}" aria-label="移除模型">${icon('close')}</button></div>`).join('');
  }
  function renderConnections() {
    screen='connections'; requestGeneration++;
    chrome(`<div class="api-layout"><nav class="api-connections" aria-label="服务连接列表"><div class="api-list-heading"><span>我的连接</span><span>${config.connections.length}</span></div>${config.connections.map(c=>`<button class="api-connection ${draft.id===c.id?'selected':''}" data-api="select" data-id="${c.id}"><strong>${esc(c.name)}</strong><small>${protocolName(c.protocol)} · ${c.models.length} 个模型</small></button>`).join('')}<button class="button api-add-connection" data-api="new">${icon('plus')}添加连接</button>${!config.connections.length?'<p class="api-list-empty">暂无连接。<br>从服务商提供的 API 信息开始填写。</p>':''}</nav><div class="api-editor"><div class="api-editor-title"><h3>${config.connections.some(c=>c.id===draft.id)?esc(draft.name):'添加服务连接'}</h3><span class="pill">配置演示</span></div>
      <div class="api-field-grid">${field('api-name','连接名称',input('api-name',draft.name,'例如：我的模型服务'))}${field('api-protocol','接口类型',`<select id="api-protocol">${option('openai','OpenAI 兼容',draft.protocol)}${option('custom','其他 / 专用接口',draft.protocol)}</select>`)}</div>
      ${field('api-url','API 地址 · Base URL',input('api-url',draft.baseUrl,'https://api.example.com/v1','url'),'按服务商提供的基础地址填写，包括需要的版本路径。')}
      ${field('api-key','API Key',`<div class="api-key-field">${input('api-key','','粘贴用于演示的 Key','password')}<button class="icon-button" data-api="toggle-key" aria-label="显示 API Key">${icon('eye')}</button></div>`)}
      <label class="api-no-key"><input id="api-no-key" type="checkbox" ${draft.noKey?'checked':''}>此连接无需 API Key</label><p id="api-key-note" class="api-field-note">${draft.noKey?'例如无需鉴权的本地服务。':'Key 不写入浏览器持久存储；请使用测试内容体验。'}</p>
      <div class="api-check-row"><button class="button" data-api="check">检查连接 <span class="muted">· 演示</span></button><details class="api-test-options"><summary>演示选项</summary><label><input id="api-simulate-failure" type="checkbox">模拟连接失败</label></details></div><p id="api-check-result" class="api-result" role="status">尚未检查</p>
      <div class="api-model-heading"><div><h3>模型</h3><small>填写模型 ID，并声明用途。能力以真实验证为准。</small></div><button class="text-button" data-api="discover">获取模型 · 演示</button></div><p id="api-protocol-note" class="api-field-note">${draft.protocol==='custom'?'专用接口需相应适配器；填写信息不表示已经支持该服务。':'兼容接口的模型列表可用于发现模型，图像与视频能力仍需分别适配验证。'}</p>
      <div id="api-model-list">${modelRows()}</div><button class="text-button" data-api="add-model">${icon('plus')}手动添加模型</button><p id="api-form-error" class="api-error" role="alert"></p>
      <div class="api-editor-footer">${config.connections.some(c=>c.id===draft.id)?'<button class="text-button api-delete" data-api="delete">删除连接</button>':'<span></span>'}<button class="button primary" data-api="save">保存连接</button></div></div></div>`);
    const keyInput=document.querySelector('#api-key'); keyInput.value=keys.get(draft.id)||''; keyInput.disabled=draft.noKey;
  }
  function assignmentOptions(cap,selected) {
    return option('','未设置',selected)+config.connections.map(c=>{
      const models=c.models.filter(m=>m.capability===cap);
      if(!models.length) return '';
      return `<optgroup label="${esc(c.name)}">${models.map(m=>option(`${c.id}/${m.uid}`,m.name||m.id,selected)).join('')}</optgroup>`;
    }).join('');
  }
  function renderAssignments() {
    screen='assignments'; requestGeneration++;
    chrome(`<div class="api-assignments"><p>从已保存的连接中选择。没有模型时，先添加连接与模型；这些选择只代表你的配置意图。</p>${purposes.map(([id,label,help,cap])=>`<div class="api-purpose"><div><label for="purpose-${id}">${label}</label><small>${help}</small></div><select id="purpose-${id}" data-purpose="${id}">${assignmentOptions(cap,config.assignments[id])}</select></div>`).join('')}<div class="api-editor-footer"><button class="text-button" data-api="connections">${icon('plus')}管理连接与模型</button><button class="button primary" data-api="save-assignments">保存用途分配</button></div></div>`);
  }
  function readForm() {
    draft.name=document.querySelector('#api-name').value.trim();
    draft.protocol=document.querySelector('#api-protocol').value;
    draft.baseUrl=document.querySelector('#api-url').value.trim();
    draft.noKey=document.querySelector('#api-no-key').checked;
    // Kept outside the serializable state even while the user edits.
    keys.set(draft.id,draft.noKey?'':document.querySelector('#api-key').value);
    document.querySelectorAll('[data-model]').forEach(row=>{
      const m=draft.models.find(m=>m.uid===row.dataset.model);
      for(const field of ['id','name','capability']) m[field]=row.querySelector(`[data-model-field="${field}"]`).value.trim();
    });
  }
  function validConnection(needsKey=false) {
    const error=document.querySelector('#api-form-error');
    if(!draft.name) { error.textContent='请给这个连接起一个名称。'; return false; }
    try {
      const url=new URL(draft.baseUrl);
      if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash) throw Error();
    } catch { error.textContent='请填写有效的 HTTP 或 HTTPS 基础地址；不要在地址中放账号、密码或查询参数。'; return false; }
    if(needsKey&&!draft.noKey&&!keys.get(draft.id)?.trim()) { error.textContent='请填写演示 Key，或勾选“此连接无需 API Key”。'; return false; }
    error.textContent=''; return true;
  }
  function removeInvalidAssignments() {
    for(const [purpose,, ,cap] of purposes) {
      const ref=config.assignments[purpose];
      if(ref&&!config.connections.some(c=>c.models.some(m=>`${c.id}/${m.uid}`===ref&&m.capability===cap))) delete config.assignments[purpose];
    }
  }
  function show(id) { selectDraft(id||config.connections[0]?.id); renderConnections(); }
  document.addEventListener('click',event=>{
    const button=event.target.closest('[data-api]'); if(!button||button.disabled) return;
    const action=button.dataset.api;
    if(screen==='connections'&&document.querySelector('#api-name')) readForm();
    switch(action) {
      case 'connections': if(!draft) selectDraft(config.connections[0]?.id); renderConnections(); break;
      case 'assignments': renderAssignments(); break;
      case 'select': selectDraft(button.dataset.id); renderConnections(); break;
      case 'new': selectDraft(); renderConnections(); break;
      case 'toggle-key': { const input=document.querySelector('#api-key'); input.type=input.type==='password'?'text':'password'; button.setAttribute('aria-label',input.type==='password'?'显示 API Key':'隐藏 API Key'); break; }
      case 'add-model': draft.models.push({uid:crypto.randomUUID(),id:'',name:'',capability:''}); renderConnections(); document.querySelector('[data-model]:last-child [data-model-field="id"]').focus(); break;
      case 'remove-model': draft.models=draft.models.filter(m=>m.uid!==button.dataset.id); renderConnections(); break;
      case 'check':
      case 'discover': {
        if(!validConnection(true)) break;
        const result=document.querySelector('#api-check-result');
        const failed=document.querySelector('#api-simulate-failure').checked;
        const generation=++requestGeneration; button.disabled=true;
        result.textContent=action==='check'?'正在演示连接检查…':'正在演示获取模型…';
        setTimeout(()=>{
          if(generation!==requestGeneration||!result.isConnected||!document.querySelector('#dialog').open) return;
          button.disabled=false;
          if(failed) { result.textContent='模拟失败：服务未响应。可检查地址与鉴权信息后重试；没有发送真实请求。'; return; }
          if(action==='check') result.textContent='模拟连接成功。尚未验证真实服务或任何模型能力。';
          else {
            if(!draft.models.some(m=>m.id==='example-model-id')) draft.models.push({uid:crypto.randomUUID(),id:'example-model-id',name:'示例模型（可改名）',capability:''});
            document.querySelector('#api-model-list').innerHTML=modelRows();
            result.textContent='已加入 1 个示例模型，请填写能力。真实模型列表尚未查询，也可直接手动填写模型 ID。';
          }
        },500); break;
      }
      case 'save': {
        if(!validConnection()) break;
        if(draft.models.some(m=>!m.id||!m.capability)) { document.querySelector('#api-form-error').textContent='请填写每个模型的 ID 和能力，或移除未填完的模型。'; break; }
        const identities=draft.models.map(m=>`${m.id}\0${m.capability}`);
        if(new Set(identities).size!==identities.length) { document.querySelector('#api-form-error').textContent='相同模型 ID 和能力已存在，请移除重复项。'; break; }
        const index=config.connections.findIndex(c=>c.id===draft.id);
        // Explicit allowlist: never spread a form or credential object into state.
        const metadata={id:draft.id,name:draft.name,protocol:draft.protocol,baseUrl:draft.baseUrl,noKey:draft.noKey,models:clone(draft.models)};
        if(index<0) config.connections.push(metadata); else config.connections[index]=metadata;
        removeInvalidAssignments(); persist(); renderConnections(); notice('连接与模型已保存。Key 只保留在当前页面内存中。'); break;
      }
      case 'delete': {
        config.connections=config.connections.filter(c=>c.id!==draft.id); keys.delete(draft.id); removeInvalidAssignments(); persist(); selectDraft(config.connections[0]?.id); renderConnections(); notice('已删除连接，并清除它的用途分配。'); break;
      }
      case 'save-assignments': {
        const assignments={}; document.querySelectorAll('[data-purpose]').forEach(input=>{ if(input.value) assignments[input.dataset.purpose]=input.value; });
        config.assignments=assignments; removeInvalidAssignments(); persist(); notice('用途分配已保存。实际调用待接入对应模型服务。'); break;
      }
    }
  });
  document.addEventListener('input',event=>{
    if(event.target.closest('.api-editor')) { requestGeneration++; const result=document.querySelector('#api-check-result'); if(result) result.textContent='配置已编辑，检查结果已失效。'; document.querySelectorAll('[data-api="check"],[data-api="discover"]').forEach(b=>b.disabled=false); }
  });
  document.addEventListener('change',event=>{
    if(event.target.id==='api-no-key') {
      const keyInput=document.querySelector('#api-key'); keyInput.disabled=event.target.checked;
      if(event.target.checked) { keyInput.value=''; keys.delete(draft.id); }
      document.querySelector('#api-key-note').textContent=event.target.checked?'例如无需鉴权的本地服务。':'Key 不写入浏览器持久存储；请使用测试内容体验。';
    }
    if(event.target.id==='api-protocol') document.querySelector('#api-protocol-note').textContent=event.target.value==='custom'?'专用接口需相应适配器；填写信息不表示已经支持该服务。':'兼容接口的模型列表可用于发现模型，图像与视频能力仍需分别适配验证。';
  });
  return { show };
}
