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

Page({
  data: {
    mode: 'all',          // all | category | search
    keyword: '',
    category: '',
    categoryName: '',
    list: [],
    page: 1,
    pageSize: 20,
    hasMore: true,
    loading: false,
    total: 0,
    theme: INIT_THEME,
    loadError: '',
    statusBarHeight: STATUS_BAR,
    navTitle: '菜谱',
  },

  onLoad(options) {
    const key = themeUtil.applyTheme();
    this.setData({ theme: key });
    const d = { page: 1, list: [], hasMore: true };
    let category = options.category || '';
    let name = options.name || '';
    let search = options.search || '';
    try { category = decodeURIComponent(category); } catch (e) {}
    try { name = decodeURIComponent(name); } catch (e) {}
    try { search = decodeURIComponent(search); } catch (e) {}
    if (category) {
      d.mode = 'category';
      d.category = category;
      d.categoryName = name || (cat.meta[category] || {}).name || '菜谱';
      d.navTitle = d.categoryName;
      wx.setNavigationBarTitle({ title: d.categoryName });
    } else if (search) {
      d.mode = 'search';
      d.keyword = search;
      d.navTitle = '搜索：' + search;
      wx.setNavigationBarTitle({ title: '搜索：' + search });
    } else {
      d.navTitle = '全部菜谱';
      wx.setNavigationBarTitle({ title: '全部菜谱' });
    }
    this.setData(d);
    this.fetch(true);
  },

  async fetch(reset) {
    if (this.data.loading) return;
    this.setData({ loading: true });
    const { mode, category, keyword, page, pageSize, theme } = this.data;
    const params = { page, pageSize };
    if (mode === 'category') params.category = category;
    if (mode === 'search') params.keyword = keyword;
    const action = mode === 'category' ? 'getByCategory' : 'getAll';
    try {
      const res = await api.call(action, params);
      const base = reset ? res.list : this.data.list.concat(res.list);
      const list = base.map((d) => ({
        ...d,
        tagColor: cat.color(d.category, theme),
        tagText: cat.textColor(d.category, theme),
      }));
      this.setData({
        list,
        total: res.total,
        hasMore: list.length < res.total,
        loading: false,
      });
    } catch (e) {
      this.setData({ loading: false, loadError: (e && e.message) || '加载失败' });
      console.error('[recipes] 加载失败:', e);
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.setData({ page: this.data.page + 1 });
      this.fetch(false);
    }
  },

  onSelect(e) {
    wx.navigateTo({ url: `/pages/detail/detail?id=${encodeURIComponent(e.detail.id)}` });
  },

  goBack() {
    const pages = getCurrentPages();
    if (pages.length > 1) {
      wx.navigateBack();
    } else {
      wx.reLaunch({ url: '/pages/index/index' });
    }
  },
});
