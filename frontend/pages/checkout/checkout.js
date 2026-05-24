// pages/checkout/checkout.js
const { request } = require('../../utils/api')
const app = getApp();
const LEVEL_CONFIG = {
  'GOLD':   { discount: 0.85, name: '黑金會員 V3', text: '85' },
  'SILVER': { discount: 0.9,  name: '白金會員 V2', text: '9' },
  'BRONZE': { discount: 1.0,  name: '黄金會員 V1', text: '' }
};
Page({
  data: {
    cartDetailList: [],
    subtotal: 0,
    userInfo: null,
    memberLevelTag: 'V1',
    memberDiscountRate: 1.0,
    memberDiscountAmount: 0,
    selectedCoupon: null,
    couponDiscountAmount: 0,
    availableCouponCount: 0,
    timeOptions: ['立即取餐'],
    selectedTimeIndex: 0,
    payableAmount: 0,
    earnedBeans: 0,
    isSubmitting: false,
  },

  onLoad() { this.generateTimeSlots(); this.fetchCoupons(); },
  onShow() {
    this.generateTimeSlots();
    this.refreshMemberInfo(); 
    const newestCoupon = app.globalData.selectedCoupon || null;    
    // 1. 優先從全局變量同步一次，保證即使 fetchCoupons 慢，UI 也能先顯示選中的券
    this.setData({
      selectedCoupon: newestCoupon || null
    }, () => {
      this.calculateCheckout(); // 先算一次
    });
  
    // 2. 再跑異步請求去校驗/刷新列表
    this.fetchCoupons();
  },

  fetchCoupons() {
    const memberId = (app.globalData.userInfo || {}).member_id;
    if (!memberId) {
      this.calculateCheckout();
      return;
    }
  
    request('/api/coupons/?member_id=' + memberId)
      .then(res => {
        if (res.success) {
          const remoteCoupons = res.coupons || [];
          app.globalData.coupons = remoteCoupons;
  
          // ✅ 新增：檢查原本選中的券是否還在可用列表裡
          // 防止後端刷新後，原本選中的券失效或數據格式變化
          if (app.globalData.selectedCoupon) {
            const stillValid = remoteCoupons.find(c => c.id === app.globalData.selectedCoupon.id && !c.is_used);
            if (!stillValid) {
              app.globalData.selectedCoupon = null; // 如果券突然失效（如過期），則清空
            } else {
              // 確保使用最新的後端數據對象，避免字段名不一致
              app.globalData.selectedCoupon = stillValid;
            }
          }
        }
      })
      .catch(err => {
        console.error('獲取優惠券失敗', err);
      })
      .finally(() => {
        // ✅ 確保這之後 setData 的 selectedCoupon 是最新的
        this.calculateCheckout();
      });
  },
  refreshMemberInfo() {
    const memberId = (app.globalData.userInfo || {}).member_id;
    console.log("當前 memberId 是:", memberId);
    if (!memberId) {
      this.calculateCheckout();
      return;
    }
  
    // 這裡直接調用接口，不再依賴 profile.js
    request('/api/member/?member_id=' + memberId)
      .then(res => {
        console.log("收到後端回傳，完整對象如下:", res);
        if (res.success && res.level) {
          const userLevel = res.level; // 拿到 "SILVER"
          const config = LEVEL_CONFIG[userLevel] || LEVEL_CONFIG['BRONZE'];
          this.setData({
            memberLevelTag: config.name,
            memberDiscountRate: config.discount,
            memberDiscountText: config.text
          }, () => {
            this.calculateCheckout(); 
          });
        }
      })
      .catch(() => {
        this.calculateCheckout(); // 失敗也要保底計算
      });
  },
  generateTimeSlots() {
    const now = new Date();
    let hours = now.getHours(), minutes = now.getMinutes();
    const slots = ['立即取餐'];
    const closeHour = 23;
    let startMinutes = Math.ceil(minutes / 15) * 15;
    if (startMinutes >= 60) { hours += 1; startMinutes = 0; }
    for (let h = hours; h < closeHour; h++) {
      let mStart = (h === hours) ? startMinutes : 0;
      for (let m = mStart; m < 60; m += 15) {
        slots.push(`${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}`);
      }
    }
    this.setData({
      timeOptions: slots,
      selectedTimeIndex: this.data.selectedTimeIndex >= slots.length ? 0 : this.data.selectedTimeIndex
    });
  },

  onTimeChange(e) { this.setData({ selectedTimeIndex: e.detail.value }); },

  calculateCheckout() {
    const cart     = app.globalData.cart || [];
    const userInfo = app.globalData.userInfo || {};
    const now      = new Date();
    
    // 1. 計算原始總價 (Raw Subtotal)
    let rawSubtotal = 0;
    cart.forEach(item => { rawSubtotal += item.totalPrice; });

    // 2. ✅ 去隱患：直接從 data 讀取由 refreshMemberInfo 設定好的折扣率
    // 如果 refreshMemberInfo 還沒跑完，預設為 1.0 (V1 原價)
    const rate = this.data.memberDiscountRate || 1.0;
    const tag  = this.data.memberLevelTag    || '黄金會員 V1';

    // 3. 計算會員折扣金額
    const memberDiscountAmount = Math.round(rawSubtotal * (1 - rate) * 10) / 10;

    // 4. 計算優惠券折扣
    const selectedCoupon = app.globalData.selectedCoupon || null;
    // 🔍 添加這行代碼來打印對象
    console.log('--- 優惠券調試信息 ---');
    console.log('已選中優惠券對象:', selectedCoupon);
    console.log('購物車小計:', rawSubtotal);
    let couponDiscountAmount = 0;
    
    if (selectedCoupon) {
      // 強制轉換類型以防萬一
      const minSpend = parseFloat(selectedCoupon.min_spend || 0);
      const discountVal = parseFloat(selectedCoupon.discount_amount || 0);
      const currentTotal = parseFloat(rawSubtotal || 0);
    
      if (currentTotal >= minSpend) {
        couponDiscountAmount = discountVal; // ✅ 賦值
        console.log('✅ 優惠券校驗通過，扣減金額:', couponDiscountAmount);
      } else {
        console.log('❌ 金額未達門檻');
      }
    }

    // 5. 計算最終應付金額
    let payableAmount = rawSubtotal - memberDiscountAmount - couponDiscountAmount;
    if (payableAmount < 0) payableAmount = 0;

    // 6. 獲取可用優惠券數量 (用於 UI 顯示)
    const availableCoupons = (app.globalData.coupons || []).filter(c => 
      !c.is_used && new Date(c.expire_date) > now
    );

    this.setData({
      cartDetailList: cart,
      userInfo: userInfo,
      availableCouponCount: availableCoupons.length,
      couponDiscountAmount: couponDiscountAmount.toFixed(1),
      selectedCoupon: selectedCoupon,
      
      // ✅ 修正 UI 顯示邏輯
      subtotal: rawSubtotal.toFixed(1),               // 顯示原始總價
      memberLevelTag: tag,                            // 顯示等級名稱
      memberDiscountRate: rate,                       // 存儲折扣率
      memberDiscountAmount: memberDiscountAmount.toFixed(1), // 顯示折扣了多少錢
      
      payableAmount: payableAmount.toFixed(1),        // 最終要付的錢
      earnedBeans: Math.floor(payableAmount)          // 本次訂單預計獲得的積分
    });
  },


  selectCoupon() { wx.navigateTo({ url: '/pages/select-coupon/select-coupon' }); },

  // ==================== 主下單流程 ====================
  confirmOrder() {
    if (this.data.cartDetailList.length === 0 || this.data.isSubmitting) return;

    wx.showModal({
      title: '確認下單',
      content: `待支付金額：MOP ${this.data.payableAmount}，是否確定提交？`,
      confirmColor: '#000000',
      success: (res) => {
        if (!res.confirm) return;

        this.setData({ isSubmitting: true });
        wx.showLoading({ title: '處理中…', mask: true });

        // 【關鍵修改】先清空所有進行中的訂單，再建立新訂單
        this.clearAllOngoingOrders()
          .then(() => this.createNewOrder())
          .catch((err) => {
            console.warn('清空進行中訂單失敗，但仍繼續下單', err);
            this.createNewOrder();
          });
      }
    });
  },

  // 清空進行中訂單（本地 + 後端）
  clearAllOngoingOrders() {
    return new Promise((resolve, reject) => {
      const memberId = (app.globalData.userInfo || {}).member_id;

      // 清本地
      app.globalData.orders = (app.globalData.orders || []).filter(o => o.type !== 'ongoing');
      wx.setStorageSync('orders', app.globalData.orders);

      if (!memberId) {
        return resolve();
      }

      // 清後端
      request('/api/orders/clear-ongoing/', 'POST', { member_id: memberId })
        .then(res => res.success ? resolve() : reject(new Error(res.error || '後端清空失敗')))
        .catch(reject);
    });
  },

  // 建立新訂單（原邏輯抽出）
  createNewOrder() {
    const finalPickupTime = this.data.timeOptions[this.data.selectedTimeIndex];
    const pickupCode      = this.generatePickupCode();
    const memberId        = (app.globalData.userInfo || {}).member_id;

    request('/api/orders/', 'POST', {
      member_id:   memberId || null,
      total_price: this.data.payableAmount,
      pickup_time: finalPickupTime,
      pickup_code: pickupCode,
      coupon_id:   this.data.selectedCoupon ? this.data.selectedCoupon.id : null,
      items: this.data.cartDetailList.map(item => ({
        id:         item.productId,
        name:       item.name,
        quantity:   item.quantity,
        price:      item.price,
        customText: item.customText,
        image:      item.image,
        customization: {
          temp:  (item.customization || {}).ice       || '',
          sugar: (item.customization || {}).sweetness || '',
          bean:  (item.customization || {}).bean      || '',
        },
      }))
    })
    .then(serverRes => {
      wx.hideLoading();
      if (!serverRes.success) throw new Error(serverRes.error || '下單失敗');

      // 使用優惠券
      if (this.data.selectedCoupon) {
        const tc = app.globalData.coupons.find(c => c.id === this.data.selectedCoupon.id);
        if (tc) tc.used = true;
        wx.setStorageSync('coupons', app.globalData.coupons);
      }

      // 加積分
      if (app.globalData.userInfo) {
        app.globalData.userInfo.points = (app.globalData.userInfo.points || 0) + this.data.earnedBeans;
        wx.setStorageSync('userInfo', app.globalData.userInfo);
      }

      // 新增本地訂單
      const newOrder = {
        id:           serverRes.order_id.toString(),
        orderNo:      serverRes.order_no,
        status:       'PENDING',
        status_label: '製作中',
        createTime:   this.getCurrentTime(),
        pickupTime:   finalPickupTime,
        totalItems:   this.data.cartDetailList.reduce((s, i) => s + i.quantity, 0),
        items:        this.data.cartDetailList.map(i => ({ 
          name: i.name, 
          quantity: i.quantity, 
          customText: i.customText, 
          image: i.image 
        })),
        subtotal:     this.data.subtotal,
        memberDiscount: this.data.memberDiscountAmount,
        couponDiscount: this.data.couponDiscountAmount,
        amount:       this.data.payableAmount,
        earnedBeans:  this.data.earnedBeans,
        pickupCode:   serverRes.pickup_code,
        type:         'ongoing',
        image:        this.data.cartDetailList.length > 0 ? this.data.cartDetailList[0].image : ''
      };

      app.addOrder(newOrder);
      app.clearCart();
      app.globalData.selectedCoupon = null;

      wx.showToast({ title: '下單成功！', icon: 'success' }); //待修改showmodal
      setTimeout(() => { wx.switchTab({ url: '/pages/order/order' }); }, 1500);
    })
    .catch(err => {
      wx.hideLoading();
      console.error('下單失敗:', err);
      wx.showToast({ title: '下單失敗，請重試', icon: 'error' });
    })
    .finally(() => {
      this.setData({ isSubmitting: false });
    });
  },

  getCurrentTime() {
    const d = new Date();
    return `${d.getFullYear()}-${(d.getMonth()+1).toString().padStart(2,'0')}-${d.getDate().toString().padStart(2,'0')} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
  },

  generatePickupCode() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    return Array.from({length: 4}, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  }
});