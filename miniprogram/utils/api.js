// 统一的后端调用封装：根据 config.mode 在云函数与本地 HTTP 之间切换
const config = require('../config.js');
const { getCloud } = require('../cloud.js');

function cloudCall(action, params) {
  return getCloud().then((cloud) => new Promise((resolve, reject) => {
    cloud.callFunction({
      name: 'getRecipes',
      data: { action, ...params },
      success: (res) => {
        const r = res.result || {};
        if (r.success) resolve(r.data);
        else {
          const msg = r.message || r.code || '云端返回失败';
          console.error('[getRecipes] 云端返回失败:', action, JSON.stringify(r));
          reject(new Error(msg));
        }
      },
      fail: (err) => {
        const msg = (err && err.errMsg) ? err.errMsg : '调用失败';
        console.error('[getRecipes] 调用失败:', action, err);
        reject(new Error(msg));
      },
    });
  }));
}

function httpCall(action, params) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: config.baseUrl + '/api',
      method: 'POST',
      data: { action, ...params },
      success: (res) => {
        const r = res.data || {};
        if (r.success) resolve(r.data);
        else reject(r.message || '调用失败');
      },
      fail: (err) => reject(err.errMsg || err),
    });
  });
}

function call(action, params = {}) {
  if (config.mode === 'http') return httpCall(action, params);
  return cloudCall(action, params);
}

module.exports = { call };
