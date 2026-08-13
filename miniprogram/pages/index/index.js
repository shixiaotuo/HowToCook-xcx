const api = require('../../utils/api.js');
const cat = require('../../utils/categories.js');
const themeUtil = require('../../utils/theme.js');

const INIT_THEME = (themeUtil.getTheme && themeUtil.getTheme().key) || 'crayon';

function getStatusBarHeight() {
  try {
    const info = (wx.getWindowInfo && wx.getWindowInfo()) || wx.getSystemInfoSync();
    return info.statusBarHeight || 20;
  } catch (e) { return 20; }
}
const STATUS_BAR = getStatusBarHeight();

// 首页每日一句话：一句吃饭的调侃，每天轮换，内容够丰富
const DAILY_QUOTES = [
  '外卖是别人的烟火，今天自己炒一盘咱家的。',
  '代码可以重构，胃不能委曲，今晚整点硬菜。',
  '泡面算应急，下厨才叫生活，今日开火。',
  '食堂的菜千篇一律，咱的锅各有脾气。',
  '不会做饭？那是从前，今天这道包你撑场。',
  '减肥明天再说，眼前这口锅先香为敬。',
  '菜市场的烟火气，是打工人的顶级疗愈。',
  '油盐酱醋齐了，这日子就有滋味了。',
  '别人点奶茶续命，我开火炒菜回魂。',
  '一粥一饭亲自动手，方知柴米香。',
  '外卖迟到是常态，自己掌勺从不鸽你。',
  '锅铲一挥，今天的不开心全给煸没了。',
  '吃是为了活着，好好吃才是为了自己。',
  '番茄炒蛋封神，新手村第一关已通关。',
  '别慌，再难的菜也就切切炒炒那点事。',
  '今日 KPI：把饭做熟，且不难吃。',
  '灶台才是真工位，烟火气里写人生。',
  '三天不沾油星人就容易发飘，今日回血。',
  '青菜豆腐保平安，粗茶淡饭最养人。',
  '下馆子花钱，下厨房花心思，后者更香。',
  '碳水使人快乐，今天的主食你说了算。',
  '凉菜热汤配齐，这顿才算圆满。',
  '炒糊了也是经验，下次火候心里有数。',
  '一碗热汤面下肚，全世界都温柔了。',
  '锅气一冒，今天就算没白活。',
  '菜单看腻了？今天让冰箱替你做主。',
  '会写 Bug 不算本事，能炒好饭才是真高手。',
  '加班可以没有尽头，晚饭必须热气腾腾。',
  '盐放多了叫风味，放少了叫清淡，都行。',
  '今天的快乐很简单：洗菜、切菜、开火、开吃。',
  '嘴上说随便，身体很诚实，它想吃口热的。',
  '把外卖的钱省下来，换成灶台上的底气。',
  '哪怕是煮个泡面，加个蛋也是认真在生活。',
  '四季更替，餐桌上的风景今天由你定。',
];

function pickDailyQuote() {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 0);
  const dayOfYear = Math.floor((now - start) / 86400000);
  return DAILY_QUOTES[dayOfYear % DAILY_QUOTES.length];
}

Page({
  data: {
    categories: [],
    total: 0,
    keyword: '',
    theme: INIT_THEME,
    dailyQuote: '',
    loadError: '',
    statusBarHeight: STATUS_BAR + 44,
  },

  onShow() {
    const key = themeUtil.applyTheme();
    this.setData({ theme: key, dailyQuote: pickDailyQuote() });
    this.loadCategories();
  },

  onThemeChange(e) {
    this.setData({ theme: e.detail.theme });
    this.loadCategories();
  },

  async loadCategories() {
    try {
      const res = await api.call('getCategories');
      const theme = this.data.theme;
      const list = (res.categories || []).map((c) => ({
        ...c,
        emoji: cat.emoji(c.key),
        color: cat.color(c.key, theme),
        colorText: cat.textColor(c.key, theme),
      }));
      // 厨房小知识统一置底
      const ti = list.findIndex((c) => c.key === 'kitchen_tips');
      if (ti >= 0) { const [kt] = list.splice(ti, 1); list.push(kt); }
      this.setData({ categories: list, total: res.total, loadError: '' });
    } catch (e) {
      console.error('[index] 分类加载失败:', e);
      this.setData({ loadError: (e && e.message) || '分类加载失败' });
      wx.showToast({ title: '分类加载失败', icon: 'none' });
    }
  },

  onSearchInput(e) {
    this.setData({ keyword: e.detail.value });
  },

  onSearch() {
    const kw = this.data.keyword.trim();
    if (!kw) {
      wx.showToast({ title: '先输入想吃的菜', icon: 'none' });
      return;
    }
    wx.navigateTo({ url: `/pages/recipes/recipes?search=${encodeURIComponent(kw)}` });
  },

  goCategory(e) {
    const { key, name } = e.currentTarget.dataset;
    wx.navigateTo({ url: `/pages/recipes/recipes?category=${key}&name=${encodeURIComponent(name)}` });
  },

  goAll() {
    wx.navigateTo({ url: '/pages/recipes/recipes' });
  },

  goRandom() {
    wx.switchTab({ url: '/pages/random/random' });
  },

  goPlan() {
    wx.switchTab({ url: '/pages/plan/plan' });
  },
});
