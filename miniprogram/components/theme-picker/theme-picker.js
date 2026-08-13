const themeUtil = require('../../utils/theme.js')

Component({
  data: {
    theme: 'crayon',
    themes: [],
    sheetShow: false,
  },

  lifetimes: {
    attached() {
      const key = themeUtil.applyTheme()
      this.setData({ theme: key, themes: themeUtil.THEMES })
    },
  },

  methods: {
    openSheet() {
      this.setData({ sheetShow: true })
    },
    closeSheet() {
      this.setData({ sheetShow: false })
    },
    // 阻止面板内容点击穿透到遮罩
    noop() {},
    pickTheme(e) {
      const key = e.currentTarget.dataset.key
      themeUtil.saveTheme(key)
      const k = themeUtil.applyTheme()
      this.setData({ theme: k, sheetShow: false })
      // 通知宿主页面更新根元素的 theme class，实现整页即时换肤
      this.triggerEvent('change', { theme: k })
    },
  },
})
