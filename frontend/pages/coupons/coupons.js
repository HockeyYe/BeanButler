// pages/coupons/coupons.js
const app = getApp();
const { request } = require('../../utils/api');

Page({
  data: {
    currentTab: 0,
    showEmpty: false,
    coupons: [],
    hasLogin: false,
  },

  onLoad() { this.init(); },
  onShow() { this.init(); },

  init() {
    const isLogin = app.globalData.hasLogin;
    this.setData({ hasLogin: isLogin });
    if (isLogin) {
      this.loadCoupons();
    } else {
      this.setData({ coupons: [], showEmpty: true });
    }
  },

  loadCoupons() {
    const memberId = (app.globalData.userInfo || {}).member_id;
    if (!memberId) return;

    wx.showLoading({ title: '載入中…' });
    request('/api/coupons/?member_id=' + memberId)
      .then(res => {
        wx.hideLoading();
        if (!res.success) return;

        // tab 0 = 可用（後端只回未使用未過期），tab 1 = 暫顯空
        const list = this.data.currentTab === 0 ? (res.coupons || []) : [];
        this.setData({ coupons: list, showEmpty: list.length === 0 });

        // 同步到 globalData 供 checkout / select-coupon 使用
        app.globalData.coupons = res.coupons || [];
      })
      .catch(() => {
        wx.hideLoading();
        this.setData({ coupons: [], showEmpty: true });
      });
  },

  switchTab(e) {
    const tab = parseInt(e.currentTarget.dataset.tab);
    this.setData({ currentTab: tab }, () => { this.loadCoupons(); });
  },

  useCoupon() {
    wx.switchTab({ url: '/pages/menu/menu' });
  },

  goToLogin() {
    wx.navigateTo({ url: '/pages/login/login' });
  }
});
