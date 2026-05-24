// index.js
Page({
  data: {
    // 首页后续需要动态绑定的数据可在此处添加
  },

  onLoad(options) {
    // 页面加载时的逻辑
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({
        selected: 0 // index页面设为0，menu页面设为1，order设为2，profile设为3
      })
    }
  },

  goToOrder() {
    wx.switchTab({
      url: '/pages/menu/menu'
    });
  }
})