// app.js
const { BASE_URL } = require('./utils/api');
App({
  globalData: {
    userInfo: null,
    hasLogin: false,
    coupons: [],
    selectedCoupon: null,
    cart: [],
    orders: [],
    BASE_URL: BASE_URL,
  },

  onLaunch() {
    // 初始化微信雲開發（僅雲端模式需要，本地模式不影響）
    if (wx.cloud) {
      wx.cloud.init({
        env: 'prod-6g0zz7ch236e5ec6',
        traceUser: true,
      });
    }

    // 讀取本地緩存
    const userInfo = wx.getStorageSync('userInfo');
    if (userInfo) {
      this.globalData.userInfo = userInfo;
      this.globalData.hasLogin = true;
    }

    const coupons = wx.getStorageSync('coupons') || [];
    this.globalData.coupons = coupons;

    const cart = wx.getStorageSync('cart') || [];
    this.globalData.cart = cart;

    // 強制清空 orders，確保不顯示虛構訂單
    this.globalData.orders = [];
    wx.setStorageSync('orders', []);

    // 記錄 logs
    const logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    wx.setStorageSync('logs', logs);

    wx.login({ success: () => {} });
  },

  login(userInfo) {
    this.globalData.userInfo = userInfo;
    this.globalData.hasLogin = true;
    wx.setStorageSync('userInfo', userInfo);
  },

  addCoupon(coupon) {
    this.globalData.coupons.push(coupon);
    wx.setStorageSync('coupons', this.globalData.coupons);
  },

  useCoupon(couponId) {
    const coupons = this.globalData.coupons.filter(c => c.id !== couponId);
    this.globalData.coupons = coupons;
    wx.setStorageSync('coupons', coupons);
  },

  getValidCoupons() {
    return this.globalData.coupons.filter(c => !c.used && new Date(c.expireDate) > new Date());
  },

  addToCart(item) {
    const cart = this.globalData.cart;
    const existingIndex = cart.findIndex(cartItem =>
      cartItem.id === item.id &&
      JSON.stringify(cartItem.customization) === JSON.stringify(item.customization)
    );
    if (existingIndex > -1) {
      cart[existingIndex].quantity += item.quantity;
      cart[existingIndex].totalPrice = cart[existingIndex].price * cart[existingIndex].quantity;
    } else {
      cart.push(item);
    }
    wx.setStorageSync('cart', cart);
  },

  updateCart(newCart) {
    this.globalData.cart = newCart;
    wx.setStorageSync('cart', newCart);
  },

  clearCart() {
    this.globalData.cart = [];
    wx.setStorageSync('cart', []);
  },

  getCartSummary() {
    const cart = this.globalData.cart;
    let totalItems = 0;
    let totalAmount = 0;
    cart.forEach(item => {
      totalItems += item.quantity;
      totalAmount += item.totalPrice;
    });
    return { totalItems, totalAmount };
  },

  addOrder(order) {
    this.globalData.orders.unshift(order);
    wx.setStorageSync('orders', this.globalData.orders);
  }
});
