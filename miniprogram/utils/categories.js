// 分类视觉元数据：emoji + 各皮肤协调色板（蜡笔风）
// 关键：每套皮肤各配一套协调色板，保证「彩虹分类」在任一皮肤下都不撞色、且标签文字可读。
const meta = {
  aquatic: { emoji: '🐟', name: '水产' },
  breakfast: { emoji: '🥞', name: '早餐' },
  condiment: { emoji: '🧂', name: '调味酱料' },
  dessert: { emoji: '🍰', name: '甜点' },
  drink: { emoji: '🥤', name: '饮品' },
  meat_dish: { emoji: '🍖', name: '荤菜' },
  'semi-finished': { emoji: '🥡', name: '半加工' },
  soup: { emoji: '🍲', name: '汤羹' },
  staple: { emoji: '🍚', name: '主食' },
  vegetable_dish: { emoji: '🥬', name: '素菜' },
  kitchen_tips: { emoji: '💡', name: '厨房小知识' },
};

// 每套皮肤一套协调色板（key 与上面 meta 一致）
const THEME_COLORS = {
  crayon: {
    aquatic: '#6BCBFF', breakfast: '#FFD93D', condiment: '#A9826A', dessert: '#FFB3C1',
    drink: '#7BD389', meat_dish: '#FF6F61', 'semi-finished': '#C9A0FF', soup: '#FFB26B',
    staple: '#8BD3A0', vegetable_dish: '#5FBF73', kitchen_tips: '#9B8CFF',
  },
  morandi: {
    aquatic: '#A9C2CB', breakfast: '#D9C18A', condiment: '#B3A89C', dessert: '#E0B7C0',
    drink: '#A9C2A9', meat_dish: '#C99BA0', 'semi-finished': '#B0A0C4', soup: '#D9B98A',
    staple: '#B6CBA9', vegetable_dish: '#9FB79A', kitchen_tips: '#B0A8D0',
  },
  fresh: {
    aquatic: '#7FB8D0', breakfast: '#E6C75A', condiment: '#6E9C8A', dessert: '#F2A9C0',
    drink: '#6BCBFF', meat_dish: '#4FB286', 'semi-finished': '#9FC2B0', soup: '#E0A86B',
    staple: '#8BD3A0', vegetable_dish: '#5FBF73', kitchen_tips: '#8FB8D8',
  },
  warm: {
    aquatic: '#F0A87C', breakfast: '#FFC857', condiment: '#C28B6E', dessert: '#FFB3C1',
    drink: '#9FD3A0', meat_dish: '#FF8A5B', 'semi-finished': '#D9A0C0', soup: '#FFB26B',
    staple: '#E0C07A', vegetable_dish: '#C2B36E', kitchen_tips: '#E0A0B0',
  },
  dark: {
    aquatic: '#7FC8E8', breakfast: '#F2D27A', condiment: '#C9B59E', dessert: '#F2B8CC',
    drink: '#A8E0BC', meat_dish: '#FF9B8E', 'semi-finished': '#D9B8F0', soup: '#FFC59A',
    staple: '#A8E0C0', vegetable_dish: '#9CD9AE', kitchen_tips: '#B8B0F0',
  },
};

// 相对亮度（0~1），用于决定标签文字用深色还是浅色
function luminance(hex) {
  const h = (hex || '#FFFFFF').replace('#', '');
  const r = parseInt(h.substr(0, 2), 16) / 255;
  const g = parseInt(h.substr(2, 2), 16) / 255;
  const b = parseInt(h.substr(4, 2), 16) / 255;
  const f = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

function color(key, theme) {
  const pal = THEME_COLORS[theme] || THEME_COLORS.crayon;
  return pal[key] || THEME_COLORS.crayon[key] || '#FF6F61';
}

// 标签文字色：亮底用深字，暗底用白字
function textColor(key, theme) {
  return luminance(color(key, theme)) > 0.55 ? '#2A2A2A' : '#FFFFFF';
}

function emoji(key) {
  return (meta[key] || {}).emoji || '🍽';
}

function name(key) {
  return (meta[key] || {}).name || '菜谱';
}

module.exports = { meta, THEME_COLORS, color, textColor, emoji, name };
