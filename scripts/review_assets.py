"""Read-only local asset inventory and review server; never calls a model."""
import json
import sqlite3
from collections import Counter
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "local-data"
OUT = DATA / "asset-review"
EXTENSIONS = {".mp4", ".mov", ".webm", ".mp3", ".wav", ".aac", ".m4a", ".flac", ".png", ".jpg", ".jpeg", ".webp", ".srt", ".vtt"}
KNOWN = {
    "b890128b40724abaa699c3fc2438def8": "已知问题：旧720P版漏独立台词、原生声重复混合，保留核对。",
    "5789bc661e4c4781b32079697e33a94a": "已知问题：继承旧版声音问题；H3结尾人物出画。",
    "befbf19903d7430a940f6d0c0d678624": "声音修正后的修改前版；独立台词已恢复。",
    "43c64984f2dd4895ace88c3306876bd9": "当前采用版；Fast结尾；机械外形连续性仍有问题。",
    "08fa2ccb614e4b08958ab95eb35f6d70": "Fast结尾补拍；机械外形与前镜头不同，待人评。",
}


def inventory():
    items, file_map, registered, failures = [], {}, set(), []
    for db in sorted(DATA.rglob("films.sqlite3")):
        with sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True) as con:
            projects = {p["id"]: p for (body,) in con.execute("SELECT body FROM projects") if (p := json.loads(body))}
            records = [(category, json.loads(body)) for category, body in con.execute("SELECT category,body FROM records WHERE category IN ('artifacts','jobs')")]
        jobs = {a["id"]: a for category, a in records if category == "jobs"}
        source = "真实制作" if db.parent == DATA else ("真实接口验证" if db.parent.name == "provider-validation" else "LLM语义测试／受控素材")
        for category, a in records:
            if category == "jobs":
                if a.get("status") != "succeeded":
                    failures.append({"project": projects.get(a.get("project_id"), {}).get("title", ""), "title": a.get("title"), "id": a["id"], "status": a.get("status"), "failure_code": a.get("failure_code"), "model": (a.get("binding") or {}).get("model"), "source": source})
                continue
            project = projects.get(a.get("project_id"), {})
            meta = a.get("meta", {})
            job = jobs.get(meta.get("job_id"), {})
            if not job:
                job = next((j for j in jobs.values() if a["id"] in j.get("artifact_ids", [])), {})
            job = {**job, "binding": job.get("binding") or {}}
            path = (db.parent / a["path"]).resolve() if a.get("path") else None
            exists = bool(path and path.is_relative_to(DATA.resolve()) and path.is_file())
            key = str(len(items))
            item = {"key": key, "id": a["id"], "title": a.get("title", a["id"]), "kind": a.get("kind", ""), "project": project.get("title", "未命名"), "source": source, "created": a.get("created", ""), "model": job.get("binding", {}).get("model", "本地派生／未记录"), "resolution": job.get("args", {}).get("parameters", {}).get("resolution", ""), "media": meta.get("media", {}), "adopted": a["id"] in project.get("adopted", {}).values(), "note": KNOWN.get(a["id"], ""), "text": a.get("text", ""), "path": str(path.relative_to(DATA)) if path and path.is_relative_to(DATA.resolve()) else "", "exists": exists, "url": f"/files/{key}" if exists else "", "extension": path.suffix.lower() if path else "", "job_id": job.get("id", "")}
            items.append(item)
            if exists:
                registered.add(path)
                file_map[key] = path
    # Include derivatives, extracted frames, subtitles, and files not registered after interrupted work.
    for path in sorted(DATA.rglob("*")):
        path = path.resolve()
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS or path in registered or path.is_relative_to(OUT.resolve()):
            continue
        if not path.is_relative_to(DATA.resolve()):
            continue
        key = str(len(items))
        rel = path.relative_to(DATA)
        group = "验证截图" if "browser-validation" in rel.parts else "派生文件／未登记文件"
        items.append({"key": key, "id": "file:" + rel.as_posix(), "title": path.name, "kind": group, "project": group, "source": group, "created": "", "model": "未单独登记；见同目录任务", "resolution": "", "media": {}, "adopted": False, "note": "可能为抽帧、规范化片段、字幕或中断后文件；不计为独立成功生成。", "text": "", "path": str(rel), "exists": True, "url": f"/files/{key}", "extension": path.suffix.lower(), "job_id": ""})
        file_map[key] = path
    result = {"items": items, "failures": failures, "counts": {"entries": len(items), "unique_files": len(set(file_map.values())), "file_entries": len(file_map), "text_entries": sum(not i["path"] for i in items), "sources": dict(Counter(i["source"] for i in items))}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result, file_map


PAGE = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>本轮资产 · 人工审阅</title>
<style>body{margin:0;background:#f5f3ee;color:#242b30;font:15px system-ui}header{padding:24px 32px;background:#fff;border-bottom:1px solid #ddd;position:sticky;top:0;z-index:2}h1{font-size:23px;margin:0 0 10px}p{line-height:1.7;margin:8px 0}select,input,button,textarea{font:inherit;padding:9px;border:1px solid #c7ccc9;border-radius:6px;background:white}input{width:250px}button,a{cursor:pointer;color:#245c54}main{padding:24px 32px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(370px,1fr));gap:20px}article{background:white;padding:18px;border:1px solid #ddd;border-radius:9px;min-width:0}h2{font-size:17px;margin:0 0 10px}img,video{width:100%;height:240px;object-fit:contain;background:#141819}audio{width:100%}small{display:block;line-height:1.7;color:#62716a;overflow-wrap:anywhere}pre{white-space:pre-wrap;max-height:320px;overflow:auto;font:14px/1.7 system-ui}textarea{box-sizing:border-box;width:100%;height:70px;margin-top:8px}.note{color:#a44824}.bar{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}.pagination{margin:20px 0}summary{cursor:pointer}.badge{color:#287b5a}</style>
<header><h1>本轮生成资产 · 人工核对</h1><p>已记录故事反馈：无聊、价值不明确、看不懂。逐项质量仍待你审核。这里的操作只保存审阅意见，不触发生成或采用版本。</p><small id="counts"></small><div class="bar"><select id="project"><option value="">全部项目</option></select><select id="type"><option value="">全部类型</option><option>视频</option><option>图片</option><option>声音</option><option>字幕</option><option>文字</option></select><select id="source"><option value="">全部来源</option></select><input id="search" placeholder="搜索镜头、模型、文件、资产ID"><button id="export">导出我的审核意见</button><a href="/manifest" target="_blank">完整清单 JSON</a></div></header>
<main><p id="summary"></p><div class="pagination"><button id="prev">上一页</button> <span id="page"></span> <button id="next">下一页</button></div><div class="grid" id="grid"></div><details style="margin-top:24px"><summary id="failureSummary"></summary><pre id="failures"></pre></details></main>
<script>
let data,filtered=[],page=0;const size=12,key='movie-agent-asset-human-review-v1';let notes={};try{notes=JSON.parse(localStorage.getItem(key)||'{}')}catch{};
const $=id=>document.getElementById(id);const el=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e};
function type(a){return ['.mp4','.mov','.webm'].includes(a.extension)?'视频':['.png','.jpg','.jpeg','.webp'].includes(a.extension)?'图片':['.wav','.mp3','.aac','.m4a','.flac'].includes(a.extension)?'声音':['.srt','.vtt'].includes(a.extension)?'字幕':'文字'}
function save(id,val){notes[id]=val;try{localStorage.setItem(key,JSON.stringify(notes))}catch{alert('浏览器保存失败，请立即导出审核意见。')}}
function render(){const q=$('search').value.toLowerCase();filtered=data.items.filter(a=>(!$('project').value||a.project===$('project').value)&&(!$('source').value||a.source===$('source').value)&&(!$('type').value||type(a)===$('type').value)&&JSON.stringify(a).toLowerCase().includes(q));page=Math.max(0,Math.min(page,Math.ceil(filtered.length/size)-1));$('summary').textContent=`筛选结果 ${filtered.length} 项。审核意见保存在当前浏览器，可导出 JSON 交给我；不会自动发送到导演。`;$('page').textContent=`${page+1} / ${Math.max(1,Math.ceil(filtered.length/size))}`;$('grid').replaceChildren();
for(const a of filtered.slice(page*size,(page+1)*size)){const card=el('article');card.append(el('h2',a.title));card.append(el('small',`${a.project} · ${a.kind} · ${a.source}`));if(a.adopted){const b=el('p','当前采用版本');b.className='badge';card.append(b)}if(a.note){const n=el('p',a.note);n.className='note';card.append(n)}
if(a.url){const t=type(a);if(t==='图片'){const m=el('img');m.src=a.url;m.loading='lazy';m.alt=a.title;card.append(m)}else if(t==='视频'||t==='声音'){const m=el(t==='视频'?'video':'audio');m.controls=true;m.preload='none';m.src=a.url;card.append(m)}const link=el('a','打开原文件 / 保存');link.href=a.url;link.target='_blank';card.append(link)}else if(a.path){card.append(el('p','登记文件缺失'))}
if(a.text){const d=el('details');d.append(el('summary','阅读完整文字'));d.append(el('pre',a.text));card.append(d)}
const streams=a.media?.streams||[];const v=streams.find(x=>x.codec_type==='video');card.append(el('small',`${a.model} · 请求 ${a.resolution||'—'} · ${v?`${v.width}×${v.height}`:''} ${a.media?.duration?Number(a.media.duration).toFixed(2)+' 秒':''}`));card.append(el('small',`资产：${a.id}`));card.append(el('small',a.path));
const status=el('select');for(const value of ['待评','通过','有问题','不采用']){const op=el('option',value);status.append(op)}status.value=notes[a.id]?.status||'待评';const note=el('textarea');note.placeholder='问题与时间点，例如：00:04 手部变形；与 SH2 人物不一致';note.value=notes[a.id]?.note||'';const persist=()=>save(a.id,{id:a.id,title:a.title,path:a.path,status:status.value,note:note.value,updated:new Date().toISOString()});status.onchange=persist;note.oninput=persist;card.append(status,note);$('grid').append(card)}
$('prev').disabled=page===0;$('next').disabled=(page+1)*size>=filtered.length;}
fetch('/manifest').then(r=>r.json()).then(d=>{data=d;$('counts').textContent=`${d.counts.unique_files} 个本地文件，${d.counts.entries} 条资产/文字记录。包含原始生成、所有旧版本、派生素材与测试资料；按来源筛选查看。`;for(const field of ['project','source'])for(const v of [...new Set(d.items.map(a=>a[field]))].sort()){const op=el('option',v);op.value=v;$(field).append(op)}$('failureSummary').textContent=`失败、未知及其他未成功任务：${d.failures.length} 条（状态不代表有可看素材）`;$('failures').textContent=d.failures.map(f=>`${f.project} | ${f.title} | ${f.status} | ${f.failure_code||''} | ${f.model||''} | ${f.id}`).join('\n');render()});
for(const id of ['project','source','type','search'])$(id).oninput=()=>{page=0;render()};$('prev').onclick=()=>{page--;render()};$('next').onclick=()=>{page++;render();window.scrollTo(0,0)};$('export').onclick=()=>{const b=new Blob([JSON.stringify({exported:new Date().toISOString(),reviews:Object.values(notes)},null,2)],{type:'application/json'});const url=URL.createObjectURL(b);const a=el('a');a.href=url;a.download='movie-agent-human-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
</script></html>'''


def app_for(result, files):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.headers.get("host") not in {"127.0.0.1:4319", "localhost:4319"} or request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"error": "local access only"}, status_code=403)
        return await call_next(request)

    @app.get("/")
    def index():
        return HTMLResponse(PAGE)

    @app.get("/manifest")
    def manifest():
        return result

    @app.get("/files/{key}")
    def file(key: str):
        path = files.get(key)
        if path is None or not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    return app


if __name__ == "__main__":
    result, files = inventory()
    print(json.dumps(result["counts"], ensure_ascii=False), flush=True)
    uvicorn.run(app_for(result, files), host="127.0.0.1", port=4319)
