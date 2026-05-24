// pages/order/order.js
const { request } = require('../../utils/api')
const app = getApp();

// ✅ 新增：把之前寫好的圖片路徑修復工具搬過來
function fixImageUrl(url) {
  if (!url) return '';
  let finalUrl = url;
  if (!finalUrl.startsWith('http')) {
    const baseUrl = app.globalData.BASE_URL || '';
    const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    const cleanPath = finalUrl.startsWith('/') ? finalUrl : '/' + finalUrl;
    finalUrl = cleanBase + cleanPath;
  }
  return finalUrl.replace(/^http:\/\//i, 'https://');
}

const STATUS_LABEL = {
  'PENDING':     '待確認',
  'CONFIRMED':   '已確認',
  'IN_PROGRESS': '製作中',
  'READY':       '待取餐',
  'PICKED_UP':   '已取餐',
};

const STATUS_COLOR = {
  'PENDING':     '#F56C6C',
  'CONFIRMED':   '#409EFF',
  'IN_PROGRESS': '#E6A23C',
  'READY':       '#9C27B0',
  'PICKED_UP':   '#67C23A',
};

const ONGOING_STATUSES = new Set(['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'READY']);

Page({
  data: {
    hasLogin: false,
    currentTab: 0,
    orders: [],
    filteredOrders: []
  },

  onLoad() { this.checkLoginStatus(); },

  onShow() {
    this.checkLoginStatus();
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 });
    }
  },

  checkLoginStatus() {
    const isLogin = app.globalData.hasLogin || false;
    this.setData({ hasLogin: isLogin });
    if (isLogin) {
      this.loadOrders();
    } else {
      this.setData({ filteredOrders: [] });
    }
  },

  loadOrders() {
    if (!this.data.hasLogin) return;
    const userInfo = app.globalData.userInfo || {};

    if (userInfo.member_id) {
      wx.showLoading({ title: '載入中…' });
      request('/api/orders/list/?member_id=' + userInfo.member_id)
        .then(res => {
          wx.hideLoading();
          if (res.success && res.orders && res.orders.length > 0) {
            const remapped = res.orders.map(o => ({
              id:           o.id,
              orderNo:      o.order_no,
              status:       o.status,
              status_label: STATUS_LABEL[o.status] || o.status,
              status_color: STATUS_COLOR[o.status] || '#909399',
              createTime:   o.create_time,
              pickupCode:   o.pickup_code,
              amount:       o.total_price,
              totalItems:   (o.items || []).reduce((s, i) => s + (i.quantity || 1), 0),
              
              items:        (o.items || []).map(i => ({ 
                ...i, 
                image: fixImageUrl(i.image) || '/images/coffee-bean-vector-icon.png' 
              })),  
              type:         ONGOING_STATUSES.has(o.status) ? 'ongoing' : 'history',
            }));
            this.setData({ orders: remapped }, () => this.filterOrders());
          } else {
            this._useLocalOrders();
          }
        })
        .catch(() => {
          wx.hideLoading();
          this._useLocalOrders();
        });
    } else {
      this._useLocalOrders();
    }
  },

  _useLocalOrders() {
    // 【關鍵修改】只使用 globalData 中真正存在的訂單，不顯示任何預設假資料
    const local = (app.globalData.orders || []).map(o => ({
      ...o,
      status_label: STATUS_LABEL[o.status] || o.status,
      status_color: STATUS_COLOR[o.status] || '#909399',
      type: ONGOING_STATUSES.has(o.status) ? 'ongoing' : 'history',
    }));
    this.setData({ orders: local }, () => this.filterOrders());
  },

  switchTab(e) {
    const tab = parseInt(e.currentTarget.dataset.tab);
    this.setData({ currentTab: tab }, () => { this.filterOrders(); });
  },

  filterOrders() {
    if (!this.data.hasLogin) return;
    const type     = this.data.currentTab === 0 ? 'ongoing' : 'history';
    const filtered = this.data.orders.filter(o => o.type === type);
    this.setData({ filteredOrders: filtered });
  },

  goToDetail(e) {
    const order = e.currentTarget.dataset.order;
    wx.showModal({
      title: '訂單詳情',
      content: `訂單號：${order.orderNo}\n狀態：${order.status_label}\n取餐碼：${order.pickupCode || '無'}`,
      showCancel: false,
      confirmColor: '#000000'
    });
  },

  goToLogin() { wx.navigateTo({ url: '/pages/login/login' }); }
});