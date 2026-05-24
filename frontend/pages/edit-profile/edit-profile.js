// pages/edit-profile/edit-profile.js
const app = getApp();
const { request } = require('../../utils/api');

Page({
  data: {
    member_id: '',
    name: '',
    student_id: '',
    phone: '',
  },

  onLoad() {
    const user = app.globalData.userInfo || wx.getStorageSync('userInfo') || {};
    this.setData({
      member_id:  user.member_id || '',
      name:       user.name || '',      // 這裡改用 user.name 對應真名
      student_id: user.student_id || '',
      phone:      user.phone || '',
    });
  },

  onNameInput(e) { this.setData({ name: e.detail.value }); },
  onStudentIdInput(e) { this.setData({ student_id: e.detail.value }); },
  onPhoneInput(e) { this.setData({ phone: e.detail.value }); },

  saveProfile() {
    const { member_id, name, student_id, phone } = this.data;

    if (!name.trim() || !student_id.trim() || !phone.trim()) {
      wx.showToast({ title: '請填寫所有欄位', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '保存中...' });

    // 修改建議：如果你的 api.js 已經有 /api，請將下方的路徑改為 '/member/update-profile/'
    const apiPath = '/api/member/update-profile/'; 

    request(apiPath, 'POST', {
      member_id: member_id,
      name: name.trim(),
      student_id: student_id.trim(),
      phone: phone.trim()
    }).then(res => {
      wx.hideLoading();
      console.log('後端原始回傳:', res);
      if (res && (res.success || res.member_id)) 
      {
        const rawData = res.data || res;
        // 同步更新全域變數與本地緩存
        const updatedUser = {
          ...app.globalData.userInfo, // 保留舊有的積分、等級等
          name:       rawData.name || this.data.name,
          nickname:   rawData.nickname || rawData.nickName || rawData.name || this.data.name,
          avatar_url: rawData.avatar_url || rawData.avatarUrl || app.globalData.userInfo.avatar_url,
          student_id: rawData.student_id || this.data.student_id,
          phone:      rawData.phone || this.data.phone,
          member_id:  rawData.member_id || this.data.member_id
        };
        app.globalData.hasLogin = true;
        wx.setStorageSync('hasLogin', true);
        
        app.globalData.userInfo = updatedUser;
        wx.setStorageSync('userInfo', updatedUser);

        wx.showToast({
          title: '資料保存成功',
          icon: 'success',
          duration: 1500,
          success: () => {
            setTimeout(() => {
              const pages = getCurrentPages();
              wx.navigateBack(); 
            }, 1500);
          }
        });
      } else {
        wx.showToast({ title: res.error || '保存失敗', icon: 'none' });
      }
    }).catch(err => {
      wx.hideLoading();
      console.error('API 請求失敗詳情:', err);
      
      // 增加診斷提示
      let errorMsg = '網路錯誤';
      if (err.statusCode === 404) {
        errorMsg = '路徑不存在(404)';
      }
      
      wx.showModal({
        title: '保存失敗',
        content: `${errorMsg}。請檢查後端接口路徑是否為: ${apiPath}`,
        showCancel: false
      });
    });
  }
});