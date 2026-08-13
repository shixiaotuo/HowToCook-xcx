// 运行配置：切换 cloud / http 模式
//  - cloud：对接 CloudBase 云函数 getRecipes（部署后填写 envId）
//  - http ：对接本地 server.js（node server.js），开发工具需勾选“不校验合法域名”
module.exports = {
  mode: 'cloud', // 本地预览：配合 node server.js；正式上传前改回 'cloud'
  envId: 'cloud1-d1gre2wrxc2bcedee', // 你的 CloudBase 环境 ID
  baseUrl: 'http://localhost:3000',
};
