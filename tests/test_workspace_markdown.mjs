import test from 'node:test';
import assert from 'node:assert/strict';
import {markdown} from '../web/workspace.js';
import {artifactRelations,libraryAssets} from '../web/panels.js';

test('common prose and shot tables have readable structure',()=>{
 const html=markdown('## 标题\n1. 开场\n2. 选择\n\n> 保持静止\n[参考](https://example.com/film)\n\n| 镜头 | 动作 |\n| --- | --- |\n| 1 | 抬头 |');
 for(const part of ['<ol start="1">','<blockquote>','<a href="https://example.com/film"','<table>','<td>抬头</td>'])assert.ok(html.includes(part),part);
});
test('untrusted output never becomes executable HTML or a javascript link',()=>{
 const html=markdown('<img src=x onerror=alert(1)>\n[链接](javascript:alert(1))\n`**code**`\n[外部](https://example.com/"onclick="bad)\n```\n<script>bad()</script>\n```');
 assert.ok(!html.includes('<img')&&!html.includes('<script>')&&!html.includes('href="javascript:'));
 assert.ok(html.includes('<code>**code**</code>'));
 assert.ok(html.includes('&quot;onclick=&quot;'));
});

test('production documents remain searchable and navigate real source versions',()=>{
 const image={id:'img',kind:'image',title:'人物图'},brief={id:'brief',kind:'production_brief',title:'说明',meta:{basis:{script:'old'}}};
 const input={id:'input',kind:'shot_input',title:'镜头输入',meta:{brief_id:'brief',asset_ids:['img']}};
 const snapshot={project:{adopted:{script:'new'}},artifacts:[image,brief,input]};
 assert.equal(libraryAssets(snapshot,{group:'documents',query:'剧本制作说明'})[0].id,'brief');
 const relationships=artifactRelations(brief,snapshot);
 assert.ok(relationships.includes('已过时')&&relationships.includes('data-id="input"'));
 assert.ok(artifactRelations(image,snapshot).includes('镜头输入'));
 assert.ok(artifactRelations(input,snapshot).includes('data-id="img"'));
});
