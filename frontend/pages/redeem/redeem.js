// pages/redeem/redeem.js
const app = getApp();
const { request } = require('../../utils/api');

Page({
  data: {
    userPoints: 0,
    options: [],   // 從後端拉的兌換選項
    isLoading: false,
  },

  onLoad() { this.init(); },
  onShow() { this.init(); },

  init() {
    this.loadUserPoints();
    this.loadOptions();
  },

  loadUserPoints() {
    if (app.globalData.hasLogin && app.globalData.userInfo) {
      this.setData({ userPoints: app.globalData.userInfo.points || 0 });
    }
  },

  loadOptions() {
    request('/api/coupons/options/')
      .then(res => {
        if (res.success) {
          this.setData({ options: res.options || [] });
        }
      })
      .catch(() => {
        // 網路失敗時用本地預設
        this.setData({
          options: [
            { id: 1, name: '滿減券 MOP 5',  min_spend: 30,  discount_amount: 5,  points_cost: 50,  validity_days: 30 },
            { id: 2, name: '滿減券 MOP 10', min_spend: 60,  discount_amount: 10, points_cost: 100, validity_days: 30 },
            { id: 3, name: '滿減券 MOP 20', min_spend: 100, discount_amount: 20, points_cost: 180, validity_days: 30 },
          ]
        });
      });
  },

  exchange(e) {
    const optionId = e.currentTarget.dataset.id;
    const option   = this.data.options.find(o => o.id === optionId);
    if (!option) return;

    if (!app.globalData.hasLogin) {
      wx.showToast({ title: '請先登入', icon: 'none' });
      setTimeout(() => { wx.navigateTo({ url: '/pages/login/login' }); }, 800);
      return;
    }

    if (this.data.userPoints < option.points_cost) {
      wx.showToast({ title: '積分不足', icon: 'none' });
      return;
    }

    wx.showModal({
      title: '確認兌換',
      content: `扣除 ${option.points_cost} 積分，兌換「${option.name}」（滿 MOP ${option.min_spend} 減 MOP ${option.discount_amount}），是否確認？`,
      confirmColor: '#000000',
      success: (res) => {
        if (res.confirm) this.doExchange(option);
      }
    });
  },

  doExchange(option) {
    if (this.data.isLoading) return;
    this.setData({ isLoading: true });
    wx.showLoading({ title: '兌換中…', mask: true });

    const memberId = (app.globalData.userInfo || {}).member_id;

    request('/api/coupons/redeem/', 'POST', {
      member_id: memberId,
      option_id: option.id,
    })
    .then(res => {
      wx.hideLoading();
      if (!res.success) {
        wx.showToast({ title: res.error || '兌換失敗', icon: 'none' });
        return;
      }

      // 更新本地積分
      app.globalData.userInfo.points = res.remaining_points;
      wx.setStorageSync('userInfo', app.globalData.userInfo);
      this.setData({ userPoints: res.remaining_points });

      wx.showModal({
        title: '兌換成功 🎉',
        content: `「${option.name}」已存入帳戶，是否立即查看？`,
        confirmText: '去查看',
        cancelText: '繼續兌換',
        confirmColor: '#000000',
        success: (r) => {
          if (r.confirm) wx.navigateTo({ url: '/pages/coupons/coupons' });
        }
      });
    })
    .catch(() => {
      wx.hideLoading();
      wx.showToast({ title: '網路錯誤，請重試', icon: 'none' });
    })
    .finally(() => {
      this.setData({ isLoading: false });
    });
  },
});
