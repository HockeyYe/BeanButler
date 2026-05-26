// pages/menu/menu.js
const app = getApp();
const { request } = require('../../utils/api');

function fixImageUrl(url) {
  if (!url) return '';
  let finalUrl = url;
  
  // 1. 如果是相對路徑，拼上雲端域名
  if (!finalUrl.startsWith('http')) {
    const baseUrl = app.globalData.BASE_URL || '';
    const cleanBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
    const cleanPath = finalUrl.startsWith('/') ? finalUrl : '/' + finalUrl;
    finalUrl = cleanBase + cleanPath;
  }
  
  // 2. 🚨 微信鐵律：強制轉換 http 為 https
  return finalUrl.replace(/^http:\/\//i, 'https://');
}

// 後端 category key → 前端分類名稱對照
const CATEGORY_MAP = {
  'ESPRESSO':     '意式咖啡',
  'POUROVER':     '手冲滴慮',
  'NON-CAFFEINE': '無咖啡因',
  'SPECIAL':      '招牌特調',
};

Page({
  data: {
    categories: [],
    currentCategory: 0,
    toView: 'cat-0',
    isTappingCategory: false,

    products: [],
    menuList: [],

    isLoading: true,


    showCustomize: false,
    currentProduct: null,
    beanOptions: [],
    iceOptions: [],
    sweetnessOptions: [],
    customization: { bean: '', sweetness: '', ice: '', quantity: 1 },

    cartTotalItems: 0,
    cartTotalAmount: 0,
    showCartDetailModal: false,
    cartDetailList: [],
    sectionHeights: []
  },

  onLoad() {
    this.loadProducts();
  },

  onShow() {
    this.loadProducts();   // Bug 5 fix: re-fetch so products marked unavailable disappear immediately
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo');
    this.setData({ userInfo });
    this.updateCartSummary();
    
    // 設定 TabBar 選中狀態
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1, showTabBar: true });
    }

    // ====================== 個人資料完整性檢查 ======================
    const user = wx.getStorageSync('userInfo') || app.globalData.userInfo || {};
    app.globalData.userInfo = user;
    this.setData({ userInfo: user });    
    // 檢查基本欄位是否存在
    const isProfileIncomplete = !user.name || !user.phone || !user.student_id;
    console.log(user.name)
    if (user.member_id && isProfileIncomplete) {
      wx.showModal({
        title: '完善資料',
        content: '請先完善個人資料，以便我們為您準備餐點',
        confirmText: '立即完善',
        cancelText: '先看看',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({ url: '/pages/edit-profile/edit-profile' });
          }
        }
      });
    }
    // =============================================================
  },

  // 從後端拉取產品
  loadProducts() {
    this.setData({ isLoading: true });

    request('/api/products/', 'GET')
      .then(res => {
        if (res && res.success) {
          // ✅ 核心修改：遍歷產品，修復圖片路徑
          let products = res.products;
          products.forEach(p => {
            p.image = fixImageUrl(p.image);
          });

          this.setData({ products: products });
          this.buildMenuList(products);
        } else {
          this.buildMenuList([]);
        }
      })
      .catch(err => {
        console.error('載入產品失敗:', err);
        this.buildMenuList([]);
      })
      .finally(() => {
        this.setData({ isLoading: false });
      });
  },

  // 拉取 AI 推薦
,

  goToAiOrder() {
    wx.navigateTo({ url: '/pages/ai-order/ai-order' });
  },

  // 組建菜單分類結構
  buildMenuList(products) {
    const hasRecommended = products.some(p => p.is_recommended);
    const catLabels = [];
    if (hasRecommended) catLabels.push('為你推荐');

    Object.values(CATEGORY_MAP).forEach(label => {
      if (products.some(p => CATEGORY_MAP[p.category] === label)) {
        catLabels.push(label);
      }
    });

    if (catLabels.length === 0) catLabels.push('菜單');

    const list = catLabels.map((cat, index) => {
      let items = [];
      if (cat === '為你推荐') {
        items = products.filter(p => p.is_recommended);
      } else {
        items = products.filter(p => CATEGORY_MAP[p.category] === cat);
      }
      return { id: 'cat-' + index, name: cat, items };
    });

    this.setData({ categories: catLabels, menuList: list }, () => {
      if (products.length > 0) {
        setTimeout(() => this.calculateHeights(), 300);
      }
    });
  },

  calculateHeights() {
    const query = wx.createSelectorQuery();
    query.selectAll('.category-section').boundingClientRect(rects => {
      if (!rects || rects.length === 0) return;
      let heights = [], top = 0;
      rects.forEach(rect => { top += rect.height; heights.push(top); });
      this.setData({ sectionHeights: heights });
    }).exec();
  },

  switchCategory(e) {
    const index = e.currentTarget.dataset.index;
    this.setData({ currentCategory: index, toView: 'cat-' + index, isTappingCategory: true });
    setTimeout(() => this.setData({ isTappingCategory: false }), 800);
  },

  onScroll(e) {
    if (this.data.isTappingCategory || this.data.sectionHeights.length === 0) return;
    let scrollTop = e.detail.scrollTop + 30;
    const heights = this.data.sectionHeights;
    for (let i = 0; i < heights.length; i++) {
      if (scrollTop < heights[i]) {
        if (this.data.currentCategory !== i) this.setData({ currentCategory: i });
        break;
      }
    }
  },

  // 打開客製化選單
  openCustomize(e) {
    let product = e.currentTarget.dataset.product;

    // ✅ 核心修復：AI 推薦的商品可能是「輕量版」，缺少溫度和甜度選項。
    // 我們用它的 id 去完整的 products 列表裡「尋寶」，找到完整版數據。
    if (this.data.products && this.data.products.length > 0) {
      const fullProduct = this.data.products.find(p => p.id === product.id);
      if (fullProduct) {
        product = fullProduct; // 狸貓換太子，把輕量版替換成完整版！
      }
    }

    const bOpts = product.allow_bean_selection ? (product.linked_beans || []) : [];
    const iOpts = product.available_temps || [];
    const sOpts = product.available_sugars || [];
    
    this.setData({
      showCustomize: true,
      currentProduct: product, // 現在這裡是完整的商品數據了
      beanOptions: bOpts, 
      iceOptions: iOpts, 
      sweetnessOptions: sOpts,
      customization: {
        bean:      bOpts.length > 0 ? bOpts[0] : null,
        ice:       iOpts.length > 0 ? iOpts[0] : null,
        sweetness: sOpts.length > 0 ? sOpts[0] : null,
        quantity:  1
      }
    });
    
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ showTabBar: false });
    }
  },

  closeCustomize() {
    this.setData({ showCustomize: false });
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ showTabBar: true });
    }
  },

  selectOption(e) {
    const type = e.currentTarget.dataset.type;
    const val  = e.currentTarget.dataset.val;
    this.setData({ [`customization.${type}`]: val });
  },

  changeQuantity(e) {
    let newVal = this.data.customization.quantity + parseInt(e.currentTarget.dataset.diff);
    if (newVal < 1) newVal = 1;
    this.setData({ 'customization.quantity': newVal });
  },

  // 加入購物車
  addToCart() {
    const { currentProduct, customization } = this.data;
    let customArr = [];
    if (customization.bean)      customArr.push(customization.bean);
    if (customization.ice)       customArr.push(customization.ice);
    if (customization.sweetness) customArr.push(customization.sweetness);

    const cartItem = {
      id:            currentProduct.id + '-' + Date.now(),
      productId:     currentProduct.id,
      name:          currentProduct.name,
      price:         currentProduct.price,
      image:         currentProduct.image,
      customization: { bean: customization.bean, sweetness: customization.sweetness, ice: customization.ice },
      customText:    customArr.join(' / '),
      quantity:      customization.quantity,
      totalPrice:    currentProduct.price * customization.quantity
    };
    app.addToCart(cartItem);
    this.updateCartSummary();
    wx.showToast({ title: '已加入', icon: 'none' });
    this.closeCustomize();
  },

  updateCartSummary() {
    const { totalItems, totalAmount } = app.getCartSummary();
    this.setData({ 
      cartTotalItems: totalItems, 
      cartTotalAmount: totalAmount,
      cartDetailList: app.globalData.cart || []
    });
    if (totalItems === 0) this.setData({ showCartDetailModal: false });
  },

  showCartDetail() {
    if (this.data.cartTotalItems > 0) {
      this.setData({ showCartDetailModal: !this.data.showCartDetailModal });
    }
  },

  closeCartDetailModal() { this.setData({ showCartDetailModal: false }); },

  removeFromCart(e) {
    const index = e.currentTarget.dataset.index;
    const cart  = app.globalData.cart;
    if (index >= 0 && index < cart.length) {
      if (cart[index].quantity > 1) {
        cart[index].quantity -= 1;
        cart[index].totalPrice = cart[index].price * cart[index].quantity;
      } else {
        cart.splice(index, 1);
      }
      app.updateCart(cart);
      this.updateCartSummary();
    }
  },

  incrementCartItem(e) {
    const index = e.currentTarget.dataset.index;
    const cart  = app.globalData.cart;
    if (index >= 0 && index < cart.length) {
      cart[index].quantity += 1;
      cart[index].totalPrice = cart[index].price * cart[index].quantity;
      app.updateCart(cart);
      this.updateCartSummary();
    }
  },

  clearCartItems() {
    wx.showModal({
      title: '清空購物車', 
      content: '确定清空已選商品嗎？', 
      confirmColor: '#000000',
      success: res => {
        if (res.confirm) {
          app.clearCart();
          this.updateCartSummary();
        }
      }
    });
  },

  // 前往結帳
  goToCheckout() {
    if (app.globalData.cart.length === 0) return;

    // 1. 檢查登錄狀態
    if (!app.globalData.hasLogin) {
      wx.showModal({
        title: '請先登錄', 
        content: '登錄後即可享受點餐服務',
        confirmText: '去登錄', 
        success: res => { 
          if (res.confirm) wx.navigateTo({ url: '/pages/login/login' }); 
        }
      });
      return;
    }

    // 2. 檢查資料完整性
    const user = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    const isProfileComplete = !!(user.name && user.phone && user.student_id);

    if (!isProfileComplete) {
      wx.showModal({
        title: '資料不完整',
        content: '下單前請先填寫您的聯絡資料',
        confirmText: '去填寫',
        showCancel: false,
        success: res => {
          if (res.confirm) wx.navigateTo({ url: '/pages/edit-profile/edit-profile' });
        }
      });
      return;
    }

    wx.navigateTo({ url: '/pages/checkout/checkout' });
  },
});
