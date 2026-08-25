// 运行配置：切换 cloud / http 模式
//  - cloud：对接 CloudBase 云函数 getRecipes（部署后填写 envId）
//  - http ：对接本地 server.js（node server.js），开发工具需勾选“不校验合法域名”
module.exports = {
  mode: 'cloud', // 本地预览：配合 node server.js；正式上传前改回 'cloud'
  envId: 'cloud1-d1g9cdbaf154ee432', // 并入「要吃啥子」共用环境（被共享方视角）
  // 环境共享：资源方（要吃啥子）的 AppID 与环境 ID，被共享方必须用实例调用
  resourceAppid: 'wx3b9e1e57123ee083', // 要吃啥子 AppID（资源方）
  resourceEnv: 'cloud1-d1g9cdbaf154ee432', // 资源方环境 ID
  baseUrl: 'http://localhost:3000',
};
