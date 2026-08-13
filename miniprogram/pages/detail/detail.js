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

// 厨房小知识正文配色：rich-text 不继承外部 CSS 主题变量，必须按当前主题注入具体色值。
// 浅色皮肤用深棕字 + 浅米底；暗夜皮肤用浅字 + 深底，保证任一皮肤下都清晰可读。
const TIP_COLORS = {
  crayon:  { text: '#4a3b2e', head: '#5a4636', border: '#e3d5c5', quoteBg: '#faf6f0', quoteText: '#6b5a4d', thBg: '#faf4ec', codeBg: '#f0ece6', hr: '#d8c8b6', quoteBorder: '#c9b79e' },
  morandi: { text: '#4a463f', head: '#574d44', border: '#ddd5cc', quoteBg: '#f5f1ec', quoteText: '#6b645c', thBg: '#f1ece6', codeBg: '#ece7e0', hr: '#d6cfc6', quoteBorder: '#c7bdb2' },
  fresh:   { text: '#3a4a40', head: '#2f4a3c', border: '#cfe3d6', quoteBg: '#eef6f1', quoteText: '#4a5a50', thBg: '#e7f1ec', codeBg: '#e3eee8', hr: '#cfe3d6', quoteBorder: '#bcd6c8' },
  warm:    { text: '#4a3a2e', head: '#5a4636', border: '#ecdcc9', quoteBg: '#fdf4ea', quoteText: '#6b5546', thBg: '#fbeede', codeBg: '#f3e8da', hr: '#e8d3bd', quoteBorder: '#e0c4a8' },
  dark:    { text: '#E8E8EE', head: '#FFC9BF', border: '#4a4a54', quoteBg: '#2A2A32', quoteText: '#B8B8C4', thBg: '#33333C', codeBg: '#2E2E36', hr: '#4a4a54', quoteBorder: '#5A4A52' },
};

// 轻量 markdown -> HTML（供 rich-text 渲染厨房小知识正文；只覆盖 tips 用到的语法）
function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function inlineMd(s, C) {
  let t = escapeHtml(s);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/\*([^*]+)\*/g, '<i>$1</i>');
  t = t.replace(/`([^`]+)`/g, `<code style="background:${C.codeBg};color:${C.text};padding:1px 6px;border-radius:5px;font-size:13px;">$1</code>`);
  return t;
}
function mdToHtml(md, theme) {
  const C = TIP_COLORS[theme] || TIP_COLORS.crayon;
  const lines = (md || '').split(/\r?\n/);
  let html = '';
  let inUl = false, inOl = false, inTable = false;
  const closeLists = () => { if (inUl) { html += '</ul>'; inUl = false; } if (inOl) { html += '</ol>'; inOl = false; } };
  const closeTable = () => { if (inTable) { html += '</tbody></table>'; inTable = false; } };
  const hSize = { 1: '19px', 2: '17px', 3: '15px', 4: '14px', 5: '13px', 6: '12px' };
  let i = 0;
  while (i < lines.length) {
    const raw = lines[i];
    const t = raw.trim();
    if (!t) { closeLists(); closeTable(); i++; continue; }
    // 表格（| a | b | 且下一行是分隔行），一次性解析整张表
    if (/^\|.*\|\s*$/.test(t) && i + 1 < lines.length && /^\|[\s:|-]+\|\s*$/.test(lines[i + 1].trim())) {
      closeLists();
      const parseRow = (row) => row.replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
      const headers = parseRow(t);
      html += `<table style="width:100%;border-collapse:collapse;margin:14px 0;font-size:13px;color:${C.text};"><thead><tr>` +
        headers.map((h) => `<th style="border:1px solid ${C.border};padding:6px 8px;text-align:left;background:${C.thBg};font-weight:800;">${inlineMd(h, C)}</th>`).join('') +
        '</tr></thead><tbody>';
      i += 2; // 跳过表头与分隔行
      while (i < lines.length && /^\|.*\|\s*$/.test(lines[i].trim())) {
        if (/^\|[\s:|-]+\|\s*$/.test(lines[i].trim())) { i++; continue; } // 跳过多余分隔行
        const cells = parseRow(lines[i].trim());
        html += '<tr>' + cells.map((c) => `<td style="border:1px solid ${C.border};padding:6px 8px;vertical-align:top;">${inlineMd(c, C)}</td>`).join('') + '</tr>';
        i++;
      }
      html += '</tbody></table>';
      continue;
    }
    closeTable();
    // 围栏代码块：``` 或 ```text 开头，收集到下一个 ``` 为止；语言标记对用户无意义，丢弃
    if (/^```/.test(t)) {
      const buf = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i].trim())) {
        buf.push(lines[i]);
        i++;
      }
      i++; // 跳过闭合的 ```
      const code = buf.join('\n');
      html += `<pre style="background:${C.codeBg};border:1px solid ${C.border};border-radius:8px;padding:12px 14px;margin:12px 0;overflow:auto;white-space:pre-wrap;word-break:break-all;font-size:13px;line-height:1.6;color:${C.text};">${escapeHtml(code)}</pre>`;
      continue;
    }
    const hm = t.match(/^(#{1,6})\s+(.*)$/);
    if (hm) {
      closeLists();
      const lvl = hm[1].length;
      html += `<h${lvl} style="font-size:${hSize[lvl]};font-weight:900;color:${C.head};margin:18px 0 8px;line-height:1.4;">${inlineMd(hm[2], C)}</h${lvl}>`;
      i++; continue;
    }
    if (t.startsWith('>')) {
      closeLists();
      html += `<blockquote style="border-left:4px solid ${C.quoteBorder};padding:6px 14px;margin:10px 0;color:${C.quoteText};background:${C.quoteBg};line-height:1.6;">${inlineMd(t.slice(1).trim(), C)}</blockquote>`;
      i++; continue;
    }
    if (/^[-*_]{3,}$/.test(t)) { closeLists(); html += `<hr style="border:none;border-top:1px dashed ${C.hr};margin:14px 0;">`; i++; continue; }
    if (/^[-*]\s+/.test(t)) {
      if (!inUl) { closeTable(); html += '<ul style="margin:6px 0;padding-left:20px;line-height:1.7;">'; inUl = true; }
      html += `<li style="margin:3px 0;color:${C.text};">${inlineMd(t.replace(/^[-*]\s+/, ''), C)}</li>`;
      i++; continue;
    }
    if (/^\d+\.\s+/.test(t)) {
      if (!inOl) { closeTable(); html += '<ol style="margin:6px 0;padding-left:22px;line-height:1.7;">'; inOl = true; }
      html += `<li style="margin:3px 0;color:${C.text};">${inlineMd(t.replace(/^\d+\.\s+/, ''), C)}</li>`;
      i++; continue;
    }
    closeLists();
    html += `<p style="margin:8px 0;line-height:1.8;font-size:14px;color:${C.text};">${inlineMd(t, C)}</p>`;
    i++;
  }
  closeLists(); closeTable();
  return html;
}

Page({
  data: {
    recipe: null,
    color: '#FF6F61',
    loading: true,
    theme: INIT_THEME,
    statusBarHeight: STATUS_BAR,
    navTitle: '',
  },

  onLoad(options) {
    const key = themeUtil.applyTheme();
    this.setData({ theme: key });
    if (!options.id) {
      wx.showToast({ title: '缺少菜谱 ID', icon: 'none' });
      return;
    }
    let id = options.id;
    try { id = decodeURIComponent(id); } catch (e) {}
    this.load(id);
  },

  onShow() {
    const key = themeUtil.applyTheme();
    if (key !== this.data.theme && this.data.recipe) {
      this.setData({
        theme: key,
        color: cat.color(this.data.recipe.category, key),
        colorText: cat.textColor(this.data.recipe.category, key),
        richContent: this.data.recipe.type === 'tip' ? mdToHtml(this.data.recipe.content || '', key) : '',
      });
    }
  },

  async load(id) {
    wx.showLoading({ title: '加载中' });
    try {
      const r = await api.call('getById', { id });
      wx.hideLoading();
      if (r && r.error) {
        wx.showToast({ title: '菜谱不存在', icon: 'none' });
        return;
      }
      this.setData({
        recipe: r,
        color: cat.color(r.category, this.data.theme),
        colorText: cat.textColor(r.category, this.data.theme),
        loading: false,
        isTip: r.type === 'tip',
        navTitle: r.name,
        richContent: r.type === 'tip' ? mdToHtml(r.content || '', this.data.theme) : '',
      });
      wx.setNavigationBarTitle({ title: r.name });
    } catch (e) {
      wx.hideLoading();
      this.setData({ loading: false });
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  previewImage(e) {
    const src = e.currentTarget.dataset.src;
    const urls = (this.data.recipe.images || []).map((p) => '/' + p);
    wx.previewImage({ current: src, urls });
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
