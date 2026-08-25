const fs = require('fs');
const cloud = require('@cloudbase/node-sdk');

const API_KEY = process.env.API_KEY;      // 你给的 JWT
const ENV_ID = process.env.ENV_ID || 'cloud1-d1gre2wrxc2bcedee';

const app = cloud.init({ env: ENV_ID, accessKey: API_KEY });

console.log('[debug] config keys:', Object.keys(app.config));
console.log('[debug] accessKey set?', !!app.config.accessKey, 'len=', (app.config.accessKey || '').length);

(async () => {
  try {
    const buf = fs.readFileSync('_covers_final/aquatic/水煮鱼/cover.jpg');
    console.log('[test] 文件字节:', buf.length);
    const res = await app.uploadFile({ cloudPath: 'covers/aquatic/__test_水煮鱼.jpg', fileContent: buf });
    console.log('[OK] fileID:', res.fileID);
  } catch (e) {
    console.log('[FAIL] message:', e && e.message);
    console.log('[FAIL] code:', e && e.code);
    console.log('[FAIL] statusCode:', e && e.statusCode);
    console.log('[FAIL] requestId:', e && e.requestId);
    const st = (e && e.stack || '').split('\n').slice(0, 6).join('\n');
    console.log('[FAIL] stack:\n' + st);
  }
})();
