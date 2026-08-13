/**
 * 本地测试服务（无需 CloudBase 即可验证 4 个能力）
 * 运行：node server.js   然后访问 http://localhost:3000
 *
 * 接口（POST /api，body 为云函数 event）：
 *   { "action": "getCategories" }
 *   { "action": "getAll", "page": 1, "pageSize": 10 }
 *   { "action": "getByCategory", "category": "aquatic" }
 *   { "action": "recommendToday", "people": 3 }
 *   { "action": "recommendPlan", "people": 2, "allergens": ["鸡蛋","虾蟹甲壳类"], "dislikes": ["香菜"] }
 *
 * 也提供 GET / 返回简单的功能说明页。
 */
const http = require('http');
const { ACTIONS, ALLERGEN_OPTIONS } = require('./cloudfunctions/getRecipes/logic');

const PORT = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (req.method === 'GET' && req.url === '/') {
    res.end(
      JSON.stringify({
        service: '程序员做饭指南 - 本地测试服务',
        actions: Object.keys(ACTIONS),
        allergenOptions: ALLERGEN_OPTIONS,
        usage: 'POST /api  with body { "action": "...", ...params }',
      })
    );
    return;
  }

  if (req.method === 'POST' && req.url === '/api') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      let event = {};
      try {
        event = body ? JSON.parse(body) : {};
      } catch (e) {
        res.statusCode = 400;
        res.end(JSON.stringify({ success: false, message: 'JSON 解析失败' }));
        return;
      }
      const { action } = event;
      if (!action || !ACTIONS[action]) {
        res.statusCode = 400;
        res.end(JSON.stringify({ success: false, code: 'INVALID_ACTION', message: `未知 action: ${action}` }));
        return;
      }
      try {
        const result = ACTIONS[action](event);
        res.end(JSON.stringify({ success: true, action, data: result }, null, 2));
      } catch (err) {
        res.statusCode = 500;
        res.end(JSON.stringify({ success: false, code: 'SERVER_ERROR', message: err.message }));
      }
    });
    return;
  }

  res.statusCode = 404;
  res.end(JSON.stringify({ success: false, message: 'Not Found' }));
});

server.listen(PORT, () => {
  console.log(`本地测试服务已启动: http://localhost:${PORT}`);
});
