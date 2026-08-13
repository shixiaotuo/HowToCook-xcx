// 主题配置与切换工具：多套皮肤，本地存储记忆
// 参考「吃饭了吗 XCX」的 theme.js 思路，变量名对齐本项目的蜡笔调色板
const THEMES = [
  { key: 'crayon', name: '蜡笔小新', navBg: '#FFF8EC', navText: 'black', swatch: '#FF6F61' },
  { key: 'morandi', name: '莫兰迪', navBg: '#F3EFEA', navText: 'black', swatch: '#C99BA0' },
  { key: 'fresh', name: '清新薄荷', navBg: '#F1F8F4', navText: 'black', swatch: '#4FB286' },
  { key: 'warm', name: '暖橙日落', navBg: '#FFF6EE', navText: 'black', swatch: '#FF8A5B' },
  { key: 'dark', name: '暗夜模式', navBg: '#1E1E22', navText: 'white', swatch: '#FF8A7A' }
]

const STORAGE_KEY = 'htc_theme'

function getTheme() {
  const key = wx.getStorageSync(STORAGE_KEY) || 'crayon'
  return THEMES.find((t) => t.key === key) || THEMES[0]
}

// 应用主题到导航栏 + 窗口背景，返回 theme key
function applyTheme() {
  const t = getTheme()
  try {
    wx.setNavigationBarColor({
      frontColor: t.navText === 'white' ? '#ffffff' : '#000000',
      backgroundColor: t.navBg
    })
    wx.setBackgroundColor({ backgroundColor: t.navBg })
  } catch (e) {}
  return t.key
}

function saveTheme(key) {
  wx.setStorageSync(STORAGE_KEY, key)
}

module.exports = { THEMES, getTheme, applyTheme, saveTheme, STORAGE_KEY }
