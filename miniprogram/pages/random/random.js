const api = require('../../utils/api.js');
const diet = require('../../utils/diet.js');
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
    people: 2,
    allergens: [],
    dislikes: '',
    allergenView: [],
    result: null,
    loading: false,
    theme: INIT_THEME,
    statusBarHeight: STATUS_BAR + 44,
  },

  // 把过敏源预算成 {name,on}，模板只判 item.on，避免依赖模板里 indexOf 求值的歧义
  buildAllergenView() {
    const set = new Set(this.data.allergens);
    const view = diet.ALLERGENS.map((name) => ({ name, on: set.has(name) }));
    this.setData({ allergenView: view });
  },

  onShow() {
    const key = themeUtil.applyTheme();
    this.setData({ theme: key });
    this.buildAllergenView();
  },

  onThemeChange(e) {
    this.setData({ theme: e.detail.theme });
  },

  changePeople(e) {
    const delta = Number(e.currentTarget.dataset.delta);
    let p = this.data.people + delta;
    p = Math.max(1, Math.min(12, p));
    this.setData({ people: p });
  },

  toggleAllergen(e) {
    const key = e.currentTarget.dataset.key;
    const set = new Set(this.data.allergens);
    if (set.has(key)) set.delete(key);
    else set.add(key);
    this.setData({ allergens: [...set] });
    this.buildAllergenView();
  },

  clearAllergens() {
    this.setData({ allergens: [] });
    this.buildAllergenView();
  },

  onDislikes(e) {
    this.setData({ dislikes: e.detail.value });
  },

  async generate() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const res = await api.call('recommendToday', {
        people: this.data.people,
        allergens: this.data.allergens,
        dislikes: diet.parseDislikes(this.data.dislikes),
      });
      this.setData({ result: res, loading: false });
    } catch (err) {
      this.setData({ loading: false });
      wx.showToast({ title: '生成失败，请重试', icon: 'none' });
    }
  },

  goDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/detail/detail?id=${encodeURIComponent(id)}` });
  },

  // 转发给好友
  onShareAppMessage() {
    return {
      title: '程序猿做饭指南｜摇一摇，今天吃啥不用愁',
      path: '/pages/random/random',
    };
  },

  // 分享到朋友圈
  onShareTimeline() {
    return {
      title: '程序猿做饭指南｜摇一摇，今天吃啥不用愁',
    };
  },
});
