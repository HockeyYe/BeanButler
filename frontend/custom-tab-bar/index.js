Component({
  data: {
    selected: 0,
    showTabBar: true, // 控制显示隐藏
    color: "#999999",
    selectedColor: "#000000",
    list: [
      { "pagePath": "/pages/index/index", "text": "首頁" },
      { "pagePath": "/pages/menu/menu", "text": "點單" },
      { "pagePath": "/pages/order/order", "text": "訂單" },
      { "pagePath": "/pages/profile/profile", "text": "我的" }
    ]
  },
  methods: {
    switchTab(e) {
      const data = e.currentTarget.dataset
      const url = data.path
      wx.switchTab({ url })
    }
  }
})