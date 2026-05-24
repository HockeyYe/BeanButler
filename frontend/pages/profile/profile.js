// pages/profile/profile.js
const app = getApp();
const { request } = require('../../utils/api');

// ✅ 新增：把後端的英文等級代碼「翻譯」成前端要顯示的中文名字
const LEVEL_DISPLAY_MAP = {
  'GOLD': '黑金會員 V3',
  'SILVER': '白金會員 V2',
  'BRONZE': '黄金會員 V1'
};

// 1. 在 checkout.js 頂部定義映射表，統一管理
const LEVEL_CONFIG = {
  'GOLD':   { discount: 0.85, name: '黑金會員 V3' },
  'SILVER': { discount: 0.9,  name: '白金會員 V2' },
  'BRONZE': { discount: 1.0,  name: '黄金會員 V1' },
}

Page({
  data: {
    hasLogin: false,
    userInfo: { avatarUrl: '', nickName: '', level: '', points: 0 }, // 將 memberLevel 改為 level
    levelDisplayName: '', // 用來存儲翻譯後的中文等級名稱
    couponCount: 0
  },

  onLoad() {
    this.checkLoginStatus();
  },

  onShow() {
    // 1. 先處理數據邏輯
    this.checkLoginStatus();
    this.refreshMemberInfo();
  
    // 2. 將 TabBar 的 Highlight 邏輯放在最後，並加入小延遲
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      setTimeout(() => {
        console.log('強制更新 TabBar 選中狀態為 3');
        this.getTabBar().setData({ 
          selected: 3 
        });
      }, 50); // 50ms 的延遲足以避開大多數渲染競爭
    }
  },

  checkLoginStatus() {
    const app = getApp();
    let u = app.globalData.userInfo;
    let isLogin = app.globalData.hasLogin; 
    // --- ✅ 修復 1：無論當前狀態如何，都嘗試從 Storage 獲取最新資料 ---
    // 這樣 edit-profile 保存後的內容才能立刻被讀取到
    const storedUserInfo = wx.getStorageSync('userInfo');
    if (storedUserInfo) {
      u = storedUserInfo;
      isLogin = true;
      app.globalData.userInfo = storedUserInfo;
      app.globalData.hasLogin = true;
    }
  
    if (isLogin && u) {
      const userLevel = u.level || 'BRONZE';
      
      // --- 核心修復：處理頭像路徑 ---
      let rawAvatar = u.avatar_url || u.avatarUrl || u.avatar || '';
      let finalAvatarUrl = rawAvatar;
  

  
      this.setData({
        hasLogin: true,
        userInfo: {
          avatarUrl:   finalAvatarUrl, 
          nickName:    u.nickname || u.nickName || '', 
          level:       userLevel,
          points:      u.points || 0
        },
        // 這裡建議確保 LEVEL_DISPLAY_MAP 在頁面外部有定義
        levelDisplayName: (typeof LEVEL_DISPLAY_MAP !== 'undefined') ? (LEVEL_DISPLAY_MAP[userLevel] || '黄金會員 V1') : '黄金會員 V1'
      });
      
      this.refreshMemberInfo();
      this.updateCouponCount();
    } else {
      this.setData({
        hasLogin: false,
        userInfo: null,
        levelDisplayName: '',
        couponCount: 0
      });
    }
  },
  // ✅ 新增：負責向後端請求優惠券數據並計算可用數量的函數
  updateCouponCount() {
    const memberId = (app.globalData.userInfo || {}).member_id;
    if (!memberId) return;

    request('/api/coupons/?member_id=' + memberId, 'GET')
      .then(res => {
        if (res.success && res.coupons) {
          const now = new Date();
          
          // 嚴格過濾：找出「還沒被使用」且「還沒過期」的優惠券
          const availableCoupons = res.coupons.filter(c => {
            const expireDate = new Date(c.expire_date);
            return !c.is_used && expireDate > now;
          });

          // 更新畫面上的數字
          this.setData({
            couponCount: availableCoupons.length
          });
          
          // 順手把最新的優惠券清單更新到全局緩存，讓其他頁面也能用
          app.globalData.coupons = res.coupons;
        }
      })
      .catch(err => {
        console.error('獲取優惠券數量失敗:', err);
      });
  },


// ... 在 Page 內 ...

  // pages/profile/profile.js

  refreshMemberInfo() {
    const memberId = (app.globalData.userInfo || {}).member_id;
    if (!memberId) return;

    request('/api/member/?member_id=' + memberId)
      .then(res => {
        if (!res.success) return;

        const latestLevel = res.level || 'BRONZE';
        const config = LEVEL_CONFIG[latestLevel] || LEVEL_CONFIG['BRONZE'];
        // --- ✅ 簡化後的邏輯：直接取值即可 ---
        // 假設後端返回的欄位名是 avatarUrl
        let finalAvatarUrl = res.avatar_url || res.avatar || '';
        // ----------------------------------

        const updatedUserInfo = { 
          ...app.globalData.userInfo, 
          ...res, 
          level: latestLevel,
          avatarUrl: finalAvatarUrl // 直接存入完整路徑
        };
        app.globalData.userInfo = updatedUserInfo;
        wx.setStorageSync('userInfo', updatedUserInfo);

        this.setData({
          'userInfo.points': res.points,
          'userInfo.level':  latestLevel,
          'userInfo.avatarUrl': finalAvatarUrl, 
          'userInfo.nickName': res.nickname || res.nickName || this.data.userInfo.nickName,
          memberLevelTag:     config.name,
          memberDiscountRate: config.discount,
          levelDisplayName:   LEVEL_DISPLAY_MAP[latestLevel] || '黄金會員 V1'
        });
      })
      .catch((err) => {
        console.error('個人中心刷新會員資料失敗：', err);
      });
  },


  goToLogin() { 
    wx.navigateTo({ url: '/pages/login/login' }); 
  },

  requireLogin(callback) {
    if (!this.data.hasLogin) {
      this.goToLogin();
    } else {
      callback();
    }
  },

  goToEditProfile() {
    wx.navigateTo({ url: '/pages/edit-profile/edit-profile' });
  },

  goToMessage() { 
    this.requireLogin(() => { wx.navigateTo({ url: '/pages/message/message' }); }); 
  },

  goToRedeem()  { 
    this.requireLogin(() => { wx.navigateTo({ url: '/pages/redeem/redeem' }); }); 
  },

  goToCoupons() { 
    this.requireLogin(() => { wx.navigateTo({ url: '/pages/coupons/coupons' }); }); 
  },

  handleLogout() {
    wx.showModal({
      title: '確認登出',
      content: '確定要退出當前帳號嗎？',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('userInfo');
          wx.removeStorageSync('member_id');
          
          if (app.globalData) {
            app.globalData.userInfo = null;
            app.globalData.hasLogin = false;
          }

          this.setData({
            hasLogin: false,
            userInfo: null,
            levelDisplayName: '',
            couponCount: 0
          });

          wx.showToast({
            title: '已成功登出',
            icon: 'success'
          });
        }
      }
    });
  }
});