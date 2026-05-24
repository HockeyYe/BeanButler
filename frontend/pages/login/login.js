// pages/login/login.js
const app = getApp();
const { request } = require('../../utils/api.js'); 

const defaultAvatarUrl = 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0'

Page({
  data: {
    avatarUrl: defaultAvatarUrl,
    nickName: ''
  },
  onLoad() {
    // 偷偷调用 wx.login 获取临时 code
    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          // 只把 code 发给后端探路，不需要带真实的头像和昵称
          request('/api/login/', 'POST', {
            code: loginRes.code,
            nickName: '微信用戶', // 后端要求有这个参数，给个默认值即可
            avatarUrl: ''
          })
          .then(res => {
            // 如果后端返回成功，并且这不是一个新用户（is_new: false）
            if (res && res.success && !res.is_new) {
              console.log("老用户静默登录成功！跳过手动输入页面");
              // 直接复用你写好的成功逻辑，瞬间跳走！
              // 注意这里传入后端返回的 name，保证名字一致
              this.onLoginSuccess(res, res.avatarUrl || this.data.avatarUrl, res.name);
            } else {
              // 如果是纯新用户（is_new: true），这里什么都不做
              // 页面会乖乖停留在当前，等待用户自己点击绿色按钮
              console.log("新用户，等待手动输入授权");
            }
          })
          .catch(err => {
            console.log('静默登录探路失败', err);
          });
        }
      }
    });
  },

  onChooseAvatar(e) {
    const { avatarUrl } = e.detail;
    this.setData({ avatarUrl });
  },

  onNickNameInput(e) {
    this.setData({ nickName: e.detail.value });
  },

  handleServiceProtocol() {
    wx.showModal({
      title: '用戶服務協議',
      content: '這裡是 Bean Butler 的服務協議內容。',
      showCancel: false,
      confirmText: '我已閱讀'
    });
  },

  handlePrivacyProtocol() {
    wx.showModal({
      title: '隱私政策',
      content: '這裡是 Bean Butler 的隱私政策內容。',
      showCancel: false,
      confirmText: '我已閱讀'
    });
  },

  // 1. 替換原有的 handleWechatLogin 函數
  handleWechatLogin() {
    const { avatarUrl, nickName } = this.data;

    if (!nickName || !nickName.trim()) {
      wx.showToast({ title: '請輸入暱稱', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '登入中...', mask: true });

    wx.login({
      success: (loginRes) => {
        if (loginRes.code) {
          // 第一步：先登錄拿 member_id (此時先不傳遞臨時頭像字串)
          request('/api/login/', 'POST', {
            code: loginRes.code,
            nickName: nickName.trim(),
            avatarUrl: '' 
          })
          .then(async (res) => {
            if (res && res.success) {
              let finalAvatarUrl = res.avatarUrl; // 暫存後端返回的頭像路徑

              // 第二步：判斷是否需要實體上傳 (如果不是預設頭像，且包含臨時路徑特徵)
              const isTempFile = avatarUrl && avatarUrl !== defaultAvatarUrl;
            
              if (isTempFile) {
                wx.showLoading({ title: '上傳頭像中...', mask: true });
                try {
                  // 呼叫我們下方新增的實體上傳函數
                  const uploadedPath = await this.uploadAvatarFile(res.member_id, avatarUrl);
                  finalAvatarUrl = uploadedPath; // 替換為真正的雲端相對路徑 (例如 /media/avatars/xxx.jpg)
                } catch (err) {
                  console.error('頭像上傳失敗:', err);
                  wx.showToast({ title: '頭像上傳失敗', icon: 'none' });
                }
              } 

              wx.hideLoading();
              // 第三步：全部完成，執行登錄成功邏輯
              this.onLoginSuccess(res, finalAvatarUrl, nickName);
            } else {
              wx.hideLoading();
              wx.showModal({
                title: '登錄失敗',
                content: res.error || '未知錯誤',
                showCancel: false
              });
            }
          })
          .catch(err => {
            wx.hideLoading();
            console.error('API Error:', err);
            wx.showModal({
              title: '網絡或伺服器錯誤',
              content: '請檢查後端服務是否正常',
              showCancel: false
            });
          });
        }
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({ title: '微信授權失敗', icon: 'none' });
      }
    });
  },

  // 2. ✅ 新增這個函數（放在 handleWechatLogin 下方即可）
  // 這個函數專門負責把 __tmp__ 文件打包送到 Django
  uploadAvatarFile(memberId, tempFilePath) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: app.globalData.BASE_URL + '/api/upload_avatar/', // 對應你 Django 剛加的路由
        filePath: tempFilePath,
        name: 'avatar', // 必須跟 Django request.FILES.get('avatar') 一致
        formData: {
          'member_id': memberId
        },
        success: (res) => {
          try {
            // wx.uploadFile 返回的 res.data 是一個 JSON 字串，需要 parse
            const data = JSON.parse(res.data);
            if (data.success) {
              resolve(data.avatarUrl); // 成功！返回 Django 給的真實路徑
            } else {
              reject(data.error);
            }
          } catch (e) {
            reject('解析上傳結果失敗');
          }
        },
        fail: (err) => reject(err)
      });
    });
  },

  onLoginSuccess(res, avatarUrl, nickName) {
    const userInfo = {
      // 統一換成 avatarUrl
      avatarUrl: res.avatarUrl || res.avatarUrl || avatarUrl, 
      // nickname 對應屏幕暱稱
      nickname:   res.nickname || res.nickName || nickName,    
      // name 對應真名
      name:       res.name || '',                              
      student_id: res.student_id || '',
      phone:      res.phone || '',
      points:     res.points || 0,
      level:      res.level || 'BRONZE',
      member_id:  res.member_id,
    };

    if (app.login) {
      app.login(userInfo);
    } else {
      app.globalData.userInfo = userInfo;
      app.globalData.hasLogin = true;
      wx.setStorageSync('userInfo', userInfo);
    }

    wx.showToast({
      title: res.is_new ? '歡迎新會員！' : '登錄成功',
      icon: 'success',
      success: () => {
        // 強制要求完善資料
        if (res.needs_profile) {
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/edit-profile/edit-profile'
            });
          }, 1500);
        } else {
          setTimeout(() => {
            this.goBack();
          }, 1500);
        }
      }
    });
  },

  goBack() {
    const pages = getCurrentPages();
    if (pages.length > 1) {
      wx.navigateBack();
    } else {
      wx.switchTab({ url: '/pages/index/index' });
    }
  }
});