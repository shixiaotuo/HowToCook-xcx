const config = require('./config.js');
const themeUtil = require('./utils/theme.js');

App({
  globalData: {},
  onLaunch() {
    // 启动即应用用户上次选择的皮肤（导航栏 + 窗口背景）
    try { themeUtil.applyTheme(); } catch (e) {}
    // 注意：并入「要吃啥子」共享环境后，前端不再用 wx.cloud.init(env: 共享环境)，
    // 而是通过 cloud.js 的 new wx.cloud.Cloud 实例调用（见 utils/api.js / pages/detail/detail.js）。
    // 故此处无需初始化主云环境。
  },
});
