/**
 * 菜谱核心逻辑（纯函数，云函数与本地服务共用）
 * 数据源：data/recipes.json（由 scripts/build-recipes.js 生成）
 */
const fs = require('fs');
const path = require('path');

const DATA_PATH = path.join(__dirname, 'data', 'recipes.json');

let _cache = null;
function loadData() {
  if (!_cache) {
    _cache = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));
  }
  return _cache;
}

// 常见过敏原 -> 需在食材文本中命中的关键词
const ALLERGEN_KEYWORDS = {
  鸡蛋: ['鸡蛋', '蛋黄', '蛋白', '蛋液', '鹌鹑蛋', '皮蛋', '咸蛋', '蛋花'],
  牛奶: ['牛奶', '奶油', '芝士', '奶酪', '黄油', '酸奶', '炼乳', '淡奶油', '芝士', '牛乳'],
  花生: ['花生'],
  坚果: ['核桃', '杏仁', '腰果', '榛子', '开心果', '巴旦木', '夏威夷果', '碧根果'],
  大豆: ['豆腐', '豆浆', '黄豆', '毛豆', '豆皮', '腐竹', '纳豆', '味噌', '豆干', '千张', '素鸡'],
  小麦麸质: ['面粉', '面条', '面包', '馒头', '包子', '饺子', '面筋', '拉面', '挂面', '面皮', '凉皮', '麦片', '吐司'],
  鱼: ['鱼', '鱼肉', '鱼片'],
  虾蟹甲壳类: ['虾', '蟹', '小龙虾', '虾仁', '蟹棒', '蟹柳'],
  贝类: ['贝', '蛤', '蛏', '蚝', '扇贝', '螺', '蚬', '生蚝', '鲍鱼'],
};

// 过敏原多选选项（供前端展示）
const ALLERGEN_OPTIONS = Object.keys(ALLERGEN_KEYWORDS).map((k) => ({ key: k, label: k }));

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function toSimple(r) {
  return {
    id: r.id,
    type: r.type || 'recipe',
    name: r.name,
    category: r.category,
    categoryName: r.categoryName,
    calories: r.calories,
    difficulty: r.difficulty,
    summary: r.summary,
    cover: Array.isArray(r.images) && r.images.length ? r.images[0] : '',
  };
}

/** 根据忌口 + 过敏原过滤 */
function filterByDiet(recipes, { allergens = [], dislikes = [] } = {}) {
  const keywords = [];
  (allergens || []).forEach((k) => {
    if (ALLERGEN_KEYWORDS[k]) keywords.push(...ALLERGEN_KEYWORDS[k]);
  });
  const dislikeWords = (dislikes || []).map((s) => String(s).trim().toLowerCase()).filter(Boolean);

  return recipes.filter((r) => {
    const text = r.searchText || '';
    for (const kw of keywords) {
      if (kw && text.includes(kw.toLowerCase())) return false;
    }
    for (const dw of dislikeWords) {
      if (dw && text.includes(dw)) return false;
    }
    return true;
  });
}

/** 1. 获取所有菜谱（简化版，分页 + 关键字/分类筛选） */
function getAll({ category, keyword, page = 1, pageSize = 30 } = {}) {
  const data = loadData();
  let list = data.recipes;
  if (category) list = list.filter((r) => r.category === category);
  if (keyword) {
    const kw = String(keyword).trim().toLowerCase();
    if (kw) list = list.filter((r) => (r.searchText || '').includes(kw));
  }
  const total = list.length;
  const p = Math.max(1, parseInt(page, 10) || 1);
  const size = Math.min(100, Math.max(1, parseInt(pageSize, 10) || 30));
  const start = (p - 1) * size;
  const items = list.slice(start, start + size).map(toSimple);
  return { total, page: p, pageSize: size, list: items };
}

/** 2. 按分类获取菜谱 */
function getByCategory({ category, keyword, page = 1, pageSize = 50 } = {}) {
  if (!category) return { error: 'category 参数必填', list: [] };
  return getAll({ category, keyword, page, pageSize });
}

/** 获取分类列表（含数量），供首页网格 */
function getCategories() {
  const data = loadData();
  return { categories: data.categories, total: data.total };
}

/** 根据 id 获取单道菜完整信息（详情页） */
function getById({ id } = {}) {
  const data = loadData();
  const r = data.recipes.find((x) => x.id === id);
  if (!r) return { error: 'not_found' };
  return r;
}

/** 从某分类抽取 n 道，尽量不重复（usedCount 记录全局使用次数） */
function selectFrom(poolByCat, category, n, usedCount, excludeToday) {
  const pool = (poolByCat[category] || []).filter((r) => !excludeToday.has(r.id));
  // 按已用次数升序，次数相同则随机，保证多样性
  const ranked = pool
    .map((r) => ({ r, w: (usedCount[r.id] || 0) + Math.random() }))
    .sort((a, b) => a.w - b.w)
    .map((x) => x.r);
  return ranked.slice(0, n);
}

function buildMenuCounts(people) {
  const p = parseInt(people, 10) || 1;
  if (p >= 5) return { meat: 3, vegetable: 2, soup: 1, staple: 1 };
  if (p >= 3) return { meat: 2, vegetable: 1, soup: 1, staple: 1 };
  return { meat: 1, vegetable: 1, soup: 0, staple: 1 };
}

/** 3. 不知道吃什么 —— 按人数推荐今日菜单 */
function recommendToday({ people = 1, allergens = [], dislikes = [] } = {}) {
  const data = loadData();
  const filtered = filterByDiet(data.recipes, { allergens, dislikes }).filter((r) => r.type !== 'tip');
  const poolByCat = {};
  filtered.forEach((r) => {
    (poolByCat[r.category] = poolByCat[r.category] || []).push(r);
  });

  const counts = buildMenuCounts(people);
  const excludeToday = new Set();
  const menu = [];

  const take = (label, cat, n) => {
    if (!n) return;
    const items = selectFrom(poolByCat, cat, n, {}, excludeToday).map(toSimple);
    items.forEach((i) => excludeToday.add(i.id));
    menu.push({ meal: label, category: cat, items });
  };

  take('早餐', 'breakfast', 1);
  take('荤菜', 'meat_dish', counts.meat);
  take('素菜', 'vegetable_dish', counts.vegetable);
  if (counts.soup) take('汤羹', 'soup', counts.soup);
  take('主食', 'staple', counts.staple);
  take('饮品', 'drink', 1);

  return {
    people: parseInt(people, 10) || 1,
    allergens,
    dislikes,
    menu,
  };
}

const WEEK_DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

/** 4. 推荐一周膳食计划（忌口 + 过敏原 + 人数） */
function recommendPlan({ people = 1, allergens = [], dislikes = [] } = {}) {
  const data = loadData();
  const filtered = filterByDiet(data.recipes, { allergens, dislikes }).filter((r) => r.type !== 'tip');
  const poolByCat = {};
  filtered.forEach((r) => {
    (poolByCat[r.category] = poolByCat[r.category] || []).push(r);
  });
  const counts = buildMenuCounts(people);
  const usedCount = {}; // id -> 本周已用次数
  const days = [];

  for (let d = 0; d < 7; d++) {
    const excludeToday = new Set();
    const pick = (cat, n) => {
      const items = selectFrom(poolByCat, cat, n, usedCount, excludeToday).map(toSimple);
      items.forEach((i) => {
        excludeToday.add(i.id);
        usedCount[i.id] = (usedCount[i.id] || 0) + 1;
      });
      return items;
    };

    const breakfast = pick('breakfast', 1);
    const lunch = [
      ...pick('meat_dish', counts.meat),
      ...pick('vegetable_dish', counts.vegetable),
      ...pick('staple', 1),
      ...(counts.soup ? pick('soup', 1) : []),
    ];
    const dinner = [
      ...pick('meat_dish', 1),
      ...pick('vegetable_dish', 1),
      ...pick('staple', 1),
    ];

    days.push({
      day: d + 1,
      label: WEEK_DAYS[d],
      meals: { breakfast, lunch, dinner },
    });
  }

  return {
    people: parseInt(people, 10) || 1,
    allergens,
    dislikes,
    days,
  };
}

const ACTIONS = {
  getAll,
  getByCategory,
  getCategories,
  getById,
  recommendToday,
  recommendPlan,
};

module.exports = {
  ACTIONS,
  ALLERGEN_OPTIONS,
  getAll,
  getByCategory,
  getCategories,
  getById,
  recommendToday,
  recommendPlan,
  filterByDiet,
};
