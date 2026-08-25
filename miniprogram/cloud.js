// 环境共享封装：HowToCook 作为「被共享方」，调用「要吃啥子」的云环境资源。
// 注意：跨小程序共享环境不能用 wx.cloud.init(env: 共享环境) + 普通 callFunction，
// 必须用 new wx.cloud.Cloud({ resourceAppid, resourceEnv }) 新建实例（官方强制要求）。
const config = require('./config.js');

let _ready = null;

// 返回已 init 完成的 cloud 实例（Promise，init 只执行一次）
function getCloud() {
  if (!_ready) {
    const instance = new wx.cloud.Cloud({
      resourceAppid: config.resourceAppid,
      resourceEnv: config.resourceEnv,
      traceUser: true,
    });
    _ready = instance.init().then(() => instance);
  }
  return _ready;
}

module.exports = { getCloud };
