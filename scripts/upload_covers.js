#!/usr/bin/env node
// 上传 _covers_final/**/cover.jpg 到 CloudBase 云存储，并回填 recipes.json 的 images/cover 字段。
// 鉴权方式：CloudBase 服务端 API Key（JWT），通过 accessKey 传入。
// 用法： API_KEY=<JWT> [ENV_ID=cloud1-xxx] [REGION=ap-shanghai] [CONC=10] node scripts/upload_covers.js
//   也可直接设置环境变量 CLOUDBASE_APIKEY=<JWT>（SDK 原生读取）。
const fs = require('fs');
const path = require('path');

const ENV_ID = process.env.ENV_ID || 'cloud1-d1g9cdbaf154ee432';
const API_KEY = process.env.API_KEY || process.env.CLOUDBASE_APIKEY;
const REGION = process.env.REGION || 'ap-shanghai';
const CONC = parseInt(process.env.CONC || '10', 10);
const ROOT = path.resolve(__dirname, '..');            // cookbook-miniprogram
const COVERS = path.join(ROOT, '_covers_final');
const MAP_OUT = path.join(__dirname, 'fileid_map.json');
const RECIPE_FILES = [
  path.join(ROOT, 'data', 'recipes.json'),
  path.join(ROOT, 'miniprogram', 'pages', 'recipes', 'recipes.json'),
  path.join(ROOT, 'cloudfunctions', 'getRecipes', 'data', 'recipes.json'),
];

if (!API_KEY) {
  console.error('[!] 缺少环境变量 API_KEY（CloudBase 服务端 API Key / JWT）'); process.exit(1);
}

const cloud = require('@cloudbase/node-sdk');
const app = cloud.init({ env: ENV_ID, accessKey: API_KEY, region: REGION });

function listCovers() {
  const out = [];
  for (const cat of fs.readdirSync(COVERS)) {
    const cd = path.join(COVERS, cat);
    if (!fs.statSync(cd).isDirectory() || cat === 'template') continue;
    for (const name of fs.readdirSync(cd)) {
      const d = path.join(cd, name);
      const f = path.join(d, 'cover.jpg');
      if (fs.statSync(d).isDirectory() && fs.existsSync(f)) out.push({ cat, name, file: f });
    }
  }
  return out;
}

// 简易并发池
async function pool(items, worker, conc) {
  const queue = items.slice();
  const running = [];
  const results = [];
  async function next() {
    if (!queue.length) return;
    const it = queue.shift();
    const r = await worker(it);
    results.push(r);
  }
  for (let i = 0; i < Math.min(conc, items.length); i++) running.push((async () => { while (queue.length) await next(); })());
  await Promise.all(running);
  return results;
}

async function main() {
  const items = listCovers();
  console.log(`[*] 待上传封面: ${items.length} 张, 并发: ${CONC}`);
  const map = {};
  const fail = [];

  await pool(items, async (it) => {
    const cloudPath = `covers/${it.cat}/${it.name}.jpg`;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const buf = fs.readFileSync(it.file);
        const res = await app.uploadFile({ cloudPath, fileContent: buf });
        map[`${it.cat}/${it.name}`] = res.fileID;
        return;
      } catch (e) {
        if (attempt === 3) {
          fail.push({ key: `${it.cat}/${it.name}`, err: String(e && e.message || e) });
          return;
        }
        await new Promise(r => setTimeout(r, 800 * attempt));
      }
    }
  }, CONC);

  console.log(`[*] 上传完成: 成功 ${Object.keys(map).length} / 失败 ${fail.length} / 共 ${items.length}`);
  fs.writeFileSync(MAP_OUT, JSON.stringify(map, null, 2));
  console.log(`[+] fileID 映射已写: ${MAP_OUT} (${Object.keys(map).length} 条)`);

  if (fail.length) {
    console.log(`\n[!] 上传失败 ${fail.length} 条，前 20 条:`);
    fail.slice(0, 20).forEach(f => console.log('   ', f.key, '->', f.err));
  }

  if (Object.keys(map).length === 0) {
    console.log('[!] 没有成功的 fileID，跳过 recipes.json 回填。');
    return;
  }
  for (const rf of RECIPE_FILES) {
    if (!fs.existsSync(rf)) { console.log(`[!] 跳过不存在: ${rf}`); continue; }
    const data = JSON.parse(fs.readFileSync(rf, 'utf-8'));
    const recs = Array.isArray(data) ? data : (data.recipes || []);
    let upd = 0;
    for (const r of recs) {
      const key = `${r.category}/${r.name}`;
      if (map[key]) { r.images = [map[key]]; r.cover = map[key]; upd++; }
    }
    fs.writeFileSync(rf, JSON.stringify(data, null, 2));
    console.log(`[+] 回填 ${rf} : ${upd} 道`);
  }
  console.log('\n=== 全部上传并回填完成 ===');
}
main().catch(e => { console.error('FATAL', e); process.exit(1); });
