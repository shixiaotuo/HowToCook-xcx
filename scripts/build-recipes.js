#!/usr/bin/env node
/**
 * 解析 Anduin2017/HowToCook 仓库，输出结构化菜谱数据。
 *
 * 输入：仓库 dishes/ 目录（文件型 <菜名>.md 或 文件夹型 <菜名>/<菜名>.md）
 * 输出：data/recipes.json —— 单源数据，供云函数/本地服务读取
 *
 * 用法：
 *   node scripts/build-recipes.js [sourceDir] [outFile]
 *   sourceDir 默认 D:/tmp/HowToCook/HowToCook-master/dishes
 */
const fs = require('fs');
const path = require('path');

const DEFAULT_SRC = 'D:/tmp/HowToCook/HowToCook-master/dishes';
const DEFAULT_OUT = path.join(__dirname, '..', 'cloudfunctions', 'getRecipes', 'data', 'recipes.json');
const DEFAULT_TIPS = 'D:/tmp/HowToCook/HowToCook-master/tips';

// HTML 实体解码（菜谱原文常含 &deg; &amp; &times; 等，直接显示会露出原始编码）
const ENTITIES = {
  deg: '°', amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ',
  times: '×', divide: '÷', plusmn: '±', mdash: '—', ndash: '–', hellip: '…',
  copy: '©', reg: '®', cent: '¢', pound: '£', yen: '¥', sup2: '²', sup3: '³',
  frac12: '½', frac14: '¼', frac34: '¾', middot: '·', bull: '•', sect: '§',
  para: '¶', laquo: '«', raquo: '»', lsquo: '‘', rsquo: '’', ldquo: '“', rdquo: '”',
};
function decodeEntities(s) {
  if (!s) return s;
  return String(s)
    .replace(/&([a-zA-Z]+);/g, (m, k) => (k.toLowerCase() in ENTITIES ? ENTITIES[k.toLowerCase()] : m))
    .replace(/&#(\d+);/g, (m, n) => String.fromCharCode(+n))
    .replace(/&#x([0-9a-fA-F]+);/g, (m, n) => String.fromCharCode(parseInt(n, 16)));
}
// 去除 markdown / LaTeX 残留（原文常用 \* \_ 防强调、用 $\pm$ $\times$ 写数学，直接显示会露出怪符号）
const LATEX = { pm: '±', times: '×', div: '÷', approx: '≈', leq: '≤', geq: '≥', neq: '≠', cdot: '·', circ: '°' };
function cleanMd(s) {
  if (!s) return s;
  s = String(s);
  s = s.replace(/!\[[^\]]*\]\([^)]*\)/g, ''); // markdown 图片 ![alt](url) -> 删除
  s = s.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1'); // markdown 链接 [text](url) -> 仅留文字
  s = s.replace(/\[\^[^\]]*\]/g, ''); // markdown 脚注引用 [^1]
  s = s.replace(/\$/g, ''); // LaTeX 数学定界符
  s = s.replace(/\\(pm|times|div|approx|leq|geq|neq|cdot|circ)\b/g, (m, k) => LATEX[k] || '');
  s = s.replace(/\\([^\s])/g, '$1'); // 其余反斜杠转义（含 \* \香 等）去掉反斜杠、保留字符
  return s;
}
function cleanAll(s) {
  return cleanMd(decodeEntities(s));
}

// 摘要：合并多段空白，并在句末（。！？」』】）截断，避免硬切字数导致半句话；
// 若 max 内无句末，则在最后逗号处断开，再不行补省略号。
function makeSummary(text, max = 110) {
  if (!text) return '';
  const flat = cleanAll(text).replace(/\s+/g, ' ').trim();
  if (flat.length <= max && /[。！？」』】]$/.test(flat)) return flat;
  const cut = flat.slice(0, max);
  const sent = cut.match(/[\s\S]*[。！？」』】]/);
  if (sent) return sent[0];
  const comma = cut.match(/[\s\S]*[，；、,]/);
  if (comma) return comma[0];
  return cut + '…';
}

const SRC = process.argv[2] || DEFAULT_SRC;
const OUT = process.argv[3] || DEFAULT_OUT;

// 分类英文目录 -> 中文展示名
const CATEGORY_MAP = {
  aquatic: '水产',
  breakfast: '早餐',
  condiment: '调味酱料',
  dessert: '甜点',
  drink: '饮品',
  meat_dish: '荤菜',
  'semi-finished': '半加工',
  soup: '汤羹',
  staple: '主食',
  vegetable_dish: '素菜',
  template: '模板',
};

// 需要跳过的分类（模板不属于可烹饪菜谱）
const SKIP_CATEGORIES = new Set(['template']);

/** 列出某个分类目录下的所有菜谱 markdown 文件 */
function listRecipeFiles(categoryDir) {
  const entries = fs.readdirSync(categoryDir, { withFileTypes: true });
  const files = [];
  for (const e of entries) {
    if (e.name === 'README.md') continue;
    if (e.isFile() && e.name.endsWith('.md')) {
      files.push({ name: e.name.replace(/\.md$/, ''), filePath: path.join(categoryDir, e.name) });
    } else if (e.isDirectory()) {
      const inner = path.join(categoryDir, e.name, e.name + '.md');
      const innerReadme = path.join(categoryDir, e.name, 'README.md');
      if (fs.existsSync(inner)) files.push({ name: e.name, filePath: inner });
      else if (fs.existsSync(innerReadme)) files.push({ name: e.name, filePath: innerReadme });
    }
  }
  return files;
}

/** 解析单个菜谱文件为结构化对象 */
function parseRecipe(category, folderName, filePath) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const lines = raw.split(/\r?\n/);

  const titleLine = lines.find((l) => l.startsWith('# '));
  const title = titleLine ? titleLine.slice(2).trim() : folderName;
  const name = (cleanAll(title).replace(/的做法$/, '').replace(/做法$/, '') || folderName).trim();

  // 简介：标题行之后、第一个“预估”或“##”之前的非空非标题行（收集为段落，最后按句末截断）
  const summaryParas = [];
  let reachedBody = false;
  for (const l of lines) {
    if (l.startsWith('# ')) { reachedBody = true; continue; }
    if (!reachedBody) continue;
    if (/预估烹饪难度|预估卡路里/.test(l)) break;
    if (l.startsWith('## ')) break;
    if (l.trim() && !l.startsWith('#')) {
      summaryParas.push(cleanAll(l.trim()));
    }
  }
  const summary = makeSummary(summaryParas.join('\n'), 110);

  const difficultyMatch = raw.match(/预估烹饪难度[:：]\s*([★☆]+)/);
  const caloriesMatch = raw.match(/预估卡路里[:：]\s*(\d+)/);
  const difficulty = difficultyMatch ? difficultyMatch[1] : '';
  const calories = caloriesMatch ? Number(caloriesMatch[1]) : null;

  // 通用：抓取某个 ## 标题 到下一个 ## 标题之间的子弹项
  const sectionBullets = (heading) => {
    const out = [];
    let inSection = false;
    for (const l of lines) {
      if (l.startsWith('## ')) {
        inSection = l.slice(3).trim() === heading;
        continue;
      }
      if (inSection && /^[-*]\s+/.test(l.trim())) {
        out.push(cleanAll(l.trim().replace(/^[-*]\s+/, '')));
      }
    }
    return out;
  };

  const ingredients = sectionBullets('必备原料和工具');

  // 计算区块可能包含 ### 辅料 / ### 香料 子标题，统一抓取全部子弹
  const ingredientDetails = (() => {
    const out = [];
    let inSection = false;
    for (const l of lines) {
      if (l.startsWith('## ')) {
        inSection = l.slice(3).trim() === '计算' || l.slice(3).trim() === '原料用量';
        continue;
      }
      if (inSection && l.startsWith('### ')) continue; // 跳过子标题
      if (inSection && /^[-*]\s+/.test(l.trim())) {
        out.push(cleanAll(l.trim().replace(/^[-*]\s+/, '')));
      }
    }
    return out;
  })();

  // 操作步骤：## 操作 区块，### 为阶段标题，数字编号行为步骤，缩进 - 为其子项
  const steps = (() => {
    const out = [];
    let inSection = false;
    let current = null;
    for (const l of lines) {
      if (l.startsWith('## ')) {
        inSection = l.slice(3).trim() === '操作';
        continue;
      }
      if (!inSection) continue;
      if (l.startsWith('### ')) { current = null; continue; } // 阶段标题仅作分隔
      const stepMatch = l.match(/^\s*(\d+)\.\s+(.*)$/);
      if (stepMatch) {
        current = { text: cleanAll(stepMatch[2].trim()), subs: [] };
        out.push(current);
      } else if (current && /^[\s　]*-+\s+/.test(l)) {
        current.subs.push(cleanAll(l.trim().replace(/^[-*]\s+/, '')));
      }
    }
    return out.map((s) => (s.subs.length ? `${s.text}（${s.subs.join('；')}）` : s.text));
  })();

  // 搜索文本：用于忌口 / 过敏原关键词过滤
  const searchText = [
    name,
    category,
    summary,
    ingredients.join(' '),
    ingredientDetails.join(' '),
  ].join(' ').toLowerCase();

  const categoryName = CATEGORY_MAP[category] || category;

  return {
    id: `${category}/${folderName}`,
    category,
    categoryName,
    name,
    title,
    summary,
    difficulty,
    calories,
    ingredients,
    ingredientDetails,
    steps,
    searchText,
    source: `https://github.com/Anduin2017/HowToCook/blob/master/dishes/${category}/${encodeURIComponent(folderName)}`,
  };
}

/** 解析单篇 tips 知识文章为结构化对象（type: 'tip'） */
function parseTip(filePath, subDir) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const lines = raw.split(/\r?\n/);
  const titleIdx = lines.findIndex((l) => /^#\s+/.test(l));
  const name = cleanAll(titleIdx >= 0 ? lines[titleIdx].replace(/^#\s+/, '').trim() : path.basename(filePath).replace(/\.md$/, ''));
  // 正文：去掉首个 H1 行，避免详情页重复标题
  const content = cleanAll((titleIdx >= 0 ? lines.slice(titleIdx + 1) : lines).join('\n').trim());
  const plain = content.replace(/[#>*_`\-|]/g, ' ').replace(/\s+/g, ' ').trim();
  const summary = makeSummary(plain, 110);
  const searchText = (name + ' ' + plain.slice(0, 500)).toLowerCase();
  const relPath = path.relative(DEFAULT_TIPS, filePath).replace(/\\/g, '/');
  return {
    id: `kitchen_tips/${path.basename(filePath).replace(/\.md$/, '')}`,
    type: 'tip',
    category: 'kitchen_tips',
    categoryName: '厨房小知识',
    subCategory: '', // 厨房小知识不再按子目录（learn/advanced）分组，统一为一个部分
    name,
    title: name,
    summary,
    content,
    difficulty: '',
    calories: null,
    ingredients: [],
    ingredientDetails: [],
    steps: [],
    images: [],
    searchText,
    source: `https://github.com/Anduin2017/HowToCook/blob/master/tips/${encodeURIComponent(relPath)}`,
  };
}

function main() {
  if (!fs.existsSync(SRC)) {
    console.error('源目录不存在:', SRC);
    process.exit(1);
  }
  // 图片清单：由 scripts/download_images.py 从 GitHub 下载真实图生成，键为 "分类/菜名"
  const manifestPath = path.join(__dirname, 'images-manifest.json');
  const imageManifest = fs.existsSync(manifestPath)
    ? JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
    : {};

  const recipes = [];
  const categories = [];
  for (const dir of fs.readdirSync(SRC, { withFileTypes: true })) {
    if (!dir.isDirectory()) continue;
    const category = dir.name;
    if (SKIP_CATEGORIES.has(category)) continue;
    const categoryName = CATEGORY_MAP[category] || category;
    const categoryDir = path.join(SRC, category);
    const files = listRecipeFiles(categoryDir);
    let count = 0;
    for (const f of files) {
      try {
        const r = parseRecipe(category, f.name, f.filePath);
        r.images = imageManifest[r.id] || [];
        recipes.push(r);
        count++;
      } catch (err) {
        console.warn('解析失败:', f.filePath, err.message);
      }
    }
    categories.push({ key: category, name: categoryName, count });
  }

  // 解析 tips 目录 -> 厨房小知识分类
  let tipsCount = 0;
  if (fs.existsSync(DEFAULT_TIPS)) {
    const walkTips = (dir, sub) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, e.name);
        if (e.isDirectory()) {
          walkTips(p, e.name);
        } else if (e.name.endsWith('.md') && e.name !== 'README.md') {
          try {
            recipes.push(parseTip(p, sub));
            tipsCount++;
          } catch (err) {
            console.warn('解析 tips 失败:', p, err.message);
          }
        }
      }
    };
    walkTips(DEFAULT_TIPS, '');
    if (tipsCount > 0) categories.push({ key: 'kitchen_tips', name: '厨房小知识', count: tipsCount });
  } else {
    console.warn('tips 目录不存在，跳过:', DEFAULT_TIPS);
  }

  categories.sort((a, b) => a.name.localeCompare(b.name, 'zh'));
  // 厨房小知识统一置底（与首页前端置底一致）
  const tiIdx = categories.findIndex((c) => c.key === 'kitchen_tips');
  if (tiIdx >= 0) { const [kt] = categories.splice(tiIdx, 1); categories.push(kt); }
  const out = {
    generatedAt: new Date().toISOString(),
    total: recipes.length,
    categories,
    recipes,
  };

  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out));
  // 同时写一份到项目 data 目录，方便查阅与本地服务
  const publicOut = path.join(__dirname, '..', 'data', 'recipes.json');
  fs.mkdirSync(path.dirname(publicOut), { recursive: true });
  fs.writeFileSync(publicOut, JSON.stringify(out));

  console.log(`解析完成：共 ${recipes.length} 道菜，输出 -> ${OUT}`);
  console.log('分类统计：');
  for (const c of categories) console.log(`  ${c.name}(${c.key}): ${c.count}`);
}

main();
