// pages/select-coupon/select-coupon.js
const app = getApp();
const { request } = require('../../utils/api');

Page({
  data: {
    coupons: [],
    showEmpty: false,
    cartTotal: 0,
  },

  onLoad() { this.loadAvailableCoupons(); },

  loadAvailableCoupons() {
    // 計算目前購物車總額（用來判斷哪張券達門檻）
    const { totalAmount } = app.getCartSummary();
    const memberId = (app.globalData.userInfo || {}).member_id;

    if (!memberId) {
      this.setData({ coupons: [], showEmpty: true, cartTotal: totalAmount });
      return;
    }

    wx.showLoading({ title: '載入中…' });
    request('/api/coupons/?member_id=' + memberId)
      .then(res => {
        wx.hideLoading();
        const all = res.success ? (res.coupons || []) : [];
        // 標記是否達到門檻
        const list = all.map(c => ({
          ...c,
          reachable: totalAmount >= c.min_spend,
        }));
        app.globalData.coupons = all;
        this.setData({ coupons: list, showEmpty: list.length === 0, cartTotal: totalAmount });
      })
      .catch(() => {
        wx.hideLoading();
        this.setData({ coupons: [], showEmpty: true, cartTotal: totalAmount });
      });
  },

  selectCoupon(e) {
    const coupon = e.currentTarget.dataset.coupon;
    if (!coupon.reachable) {
      wx.showToast({ title: `消費未達 MOP ${coupon.min_spend}`, icon: 'none' });
      return;
    }
    app.globalData.selectedCoupon = coupon;
    wx.navigateBack();
  },

  selectNone() {
    app.globalData.selectedCoupon = null;
    wx.navigateBack();
  }
});
