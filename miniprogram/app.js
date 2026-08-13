const config = require('./config.js');
const themeUtil = require('./utils/theme.js');

App({
  globalData: {},
  onLaunch() {
    // 启动即应用用户上次选择的皮肤（导航栏 + 窗口背景）
    try { themeUtil.applyTheme(); } catch (e) {}
    if (config.mode === 'cloud') {
      if (!wx.cloud) {
        console.error('当前基础库不支持云开发，请使用 2.2.3 以上的基础库');
        return;
      }
      wx.cloud.init({
        env: config.envId || '',
        traceUser: true,
      });
    }
  },
});
