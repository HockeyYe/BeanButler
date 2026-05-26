// pages/ai-order/ai-order.js
const app = getApp();
const { request } = require('../../utils/api');

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

function formatOptionValue(temperature, sugar, milk) {
  const labels = [];
  if (temperature === 'HOT') labels.push('热');
  else if (temperature === 'ICE') labels.push('冰');
  else if (temperature === 'MEDIUM') labels.push('温');

  if (sugar === 'LESS') labels.push('少糖');
  else if (sugar === 'NONE') labels.push('无糖');
  else if (sugar === 'HALF') labels.push('半糖');
  else if (sugar === 'NORMAL') labels.push('正常糖');

  const milkValue = (milk || '').toString().trim();
  const milkNorm = milkValue.toLowerCase();
  if (milkNorm === 'none') labels.push('无奶');
  else if (milkNorm === 'milk') labels.push('加奶');
  else if (milkNorm === 'oat' || milkNorm === 'oat_milk') labels.push('燕麦奶');
  else if (milkNorm === 'almond' || milkNorm === 'almond_milk') labels.push('杏仁奶');
  else if (milkNorm === 'soy' || milkNorm === 'soy_milk') labels.push('豆奶');
  else if (milkNorm === 'whole' || milkNorm === 'whole_milk') labels.push('全脂奶');

  return labels;
}

Page({
  data: {
    navBarHeight: 44,
    statusBarHeight: 20,
    navTop: 0,

    userInput: '',
    loading: false,

    hasResults: false,
    hasError: false,
    errorMessage: '',
    isFallback: false,

    recommendations: [],
    intent: '',
    followUp: '',

    promptChips: [
      { emoji: '🧊', text: '冰的、低糖、不要牛奶的咖啡' },
      { emoji: '☕', text: '热的、加燕麦奶、不加糖' },
      { emoji: '🫘', text: '手冲、花果香、预算30内' }
    ]
  },

  onLoad() {
    const sysInfo = wx.getSystemInfoSync();
    const menuBtn = wx.getMenuButtonBoundingClientRect();
    this.setData({
      statusBarHeight: sysInfo.statusBarHeight,
      navBarHeight: menuBtn.height + (menuBtn.top - sysInfo.statusBarHeight) * 2,
      navTop: menuBtn.top
    });

    this.fetchProducts();
  },

  fetchProducts() {
    const cached = wx.getStorageSync('menu_products_cache');
    const cacheTime = wx.getStorageSync('menu_products_cache_time') || 0;
    const now = Date.now();

    if (cached && (now - cacheTime < 10 * 60 * 1000)) {
      this.productsMap = cached;
      return;
    }

    request('/api/products/', 'GET').then(res => {
      if (res && res.products) {
        const map = {};
        (res.products || res.results || []).forEach(p => {
          map[p.id] = p;
        });
        this.productsMap = map;
        wx.setStorageSync('menu_products_cache', map);
        wx.setStorageSync('menu_products_cache_time', now);
      }
    }).catch(() => {});
  },

  onInput(e) {
    this.setData({ userInput: e.detail.value });
  },

  tapPromptChip(e) {
    const text = e.currentTarget.dataset.text;
    this.setData({ userInput: text });
  },

  checkLogin() {
    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo');
    if (!userInfo || !userInfo.member_id) {
      wx.showModal({
        title: '请先登录',
        content: '使用 AI 点单需要先登录账号',
        confirmText: '去登录',
        success: res => {
          if (res.confirm) {
            wx.navigateTo({ url: '/pages/login/login' });
          }
        }
      });
      return false;
    }
    return true;
  },

  sendOrder() {
    const { userInput, loading } = this.data;
    if (loading) return;
    const trimmed = userInput.trim();
    if (!trimmed) {
      wx.showToast({ title: '请输入你的需求', icon: 'none' });
      return;
    }

    if (!this.checkLogin()) return;

    this.setData({
      loading: true,
      hasResults: false,
      hasError: false,
      isFallback: false,
      recommendations: []
    });

    const userInfo = app.globalData.userInfo || wx.getStorageSync('userInfo');

    request('/api/ai/order-assistant/', 'POST', {
      user_input: trimmed,
      user_id: userInfo.member_id || 1
    }).then(res => {
      this.setData({ loading: false });

      if (!res || !res.success) {
        const msg = (res && res.message) || '服务异常，请稍后重试';

        if (res && res.data && res.data.intent === 'login_required') {
          wx.showModal({
            title: '请先登录',
            content: msg,
            confirmText: '去登录',
            success: r => {
              if (r.confirm) wx.navigateTo({ url: '/pages/login/login' });
            }
          });
          return;
        }

        this.setData({
          hasError: true,
          errorMessage: msg
        });
        return;
      }

      const data = res.data || {};
      const recs = data.recommendations || [];

      if (recs.length === 0) {
        this.setData({
          hasError: true,
          isFallback: data.is_fallback || false,
          errorMessage: '暂时没有找到匹配的饮品，试试换个说法？'
        });
        return;
      }

      const enriched = recs.map((r, idx) => {
        const product = this.productsMap && this.productsMap[r.product_id];
        let image = '/images/default.png';
        let price = '';
        let productName = r.product_name || '';

        if (product) {
          image = product.image ? fixImageUrl(product.image) : '/images/default.png';
          price = product.min_price_display || product.display_price || '';

          const sizes = (product.available_sizes && product.available_sizes.length > 0)
            ? product.available_sizes
            : (product.min_price_config ? [product.min_price_config] : []);
          if (!price && sizes.length > 0) {
            if (sizes[0].price) {
              price = 'MOP ' + sizes[0].price;
            }
          }

          if (!productName && product.name) {
            productName = product.name;
          }
        }

        const options = r.options || {};
        const optionLabels = formatOptionValue(
          options.temperature, options.sugar, options.milk
        );

        return {
          ...r,
          product_name: productName || r.product_name,
          image,
          price,
          optionLabels,
          matchTag: 'AI 推荐',
          reason: r.reason || '根据你的偏好为你推荐'
        };
      });

      this.setData({
        hasResults: true,
        recommendations: enriched,
        intent: data.intent || 'recommend_drink',
        followUp: data.follow_up_question || '',
        isFallback: data.is_fallback || false
      });
    }).catch(() => {
      this.setData({
        loading: false,
        hasError: true,
        errorMessage: '网络异常，请检查连接后重试'
      });
    });
  },

  startOver() {
    this.setData({
      userInput: '',
      hasResults: false,
      hasError: false,
      recommendations: [],
      isFallback: false
    });
  },

  goBack() {
    const pages = getCurrentPages();
    if (pages.length > 1) {
      wx.navigateBack({ delta: 1 });
    } else {
      wx.switchTab({ url: '/pages/menu/menu' });
    }
  },

  selectProduct(e) {
    const product = e.currentTarget.dataset.product;
    if (!product) return;
    wx.showToast({ title: '选购功能即将开放，敬请期待', icon: 'none', duration: 2000 });
  }
});
