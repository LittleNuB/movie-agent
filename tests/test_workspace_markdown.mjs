import test from 'node:test';
import assert from 'node:assert/strict';
import {markdown} from '../web/workspace.js';

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
