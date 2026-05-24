/**
 * utils/api.js
 * 
 * ENV 切換：
 *   'local'  → 打本地 Django (127.0.0.1:8000)
 *   'cloud'  → 打騰訊雲托管 (wx.cloud.callContainer)
 */
const ENV = 'local';

// ── 本地設定 ──────────────────────────────────────────────
// 微信開發工具模擬器用 127.0.0.1
// 真機調試請換成你 Mac 的區網 IP，例如 'http://192.168.1.100:8000'
const LOCAL_BASE_URL = 'http://127.0.0.1:8000';

// ── 雲端設定（切回雲端時用）─────────────────────────────
const ENV_ID = 'prod-6g0zz7ch236e5ec6';
const SERVICE_NAME = 'beanbulter';

// 供其他頁面組合圖片 URL 用：
// 例如 api.BASE_URL + res.image_url
const BASE_URL = ENV === 'local' ? LOCAL_BASE_URL : 'https://beanbulter-236914-8-1414261904.sh.run.tcloudbase.com';

// ─────────────────────────────────────────────────────────

function normalizePath(path) {
  let p = path;
  // 如果傳入完整 URL，截取路徑部分
  if (p.indexOf('http') !== -1) {
    const parts = p.split('.com');
    p = parts.length > 1 ? parts[1] : p;
  }
  if (!p.startsWith('/')) p = '/' + p;
  return p;
}

function requestLocal(path, method, data) {
  const safePath = normalizePath(path);
  const url = LOCAL_BASE_URL + safePath;

  return new Promise((resolve, reject) => {
    wx.request({
      url,
      method,
      data,
      header: { 'content-type': 'application/json' },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          console.error('Django 返回錯誤:', res.statusCode, res.data);
          resolve({
            success: false,
            error: (res.data && res.data.error) || '伺服器異常',
            statusCode: res.statusCode
          });
        }
      },
      fail(err) {
        console.error('本地請求失敗:', err);
        wx.showModal({
          title: '連線失敗',
          content: `無法連到本地後端\nURL: ${url}\nErr: ${err.errMsg}\n\n請確認 Django 已啟動（bash start.sh）`,
          showCancel: false
        });
        reject(err);
      }
    });
  });
}

function requestCloud(path, method, data) {
  const safePath = normalizePath(path);

  if (!wx.cloud) {
    console.error('基礎庫版本過低，請升級微信');
  } else {
    wx.cloud.init({ env: ENV_ID, traceUser: true });
  }

  return new Promise((resolve, reject) => {
    wx.cloud.callContainer({
      config: { env: ENV_ID },
      path: safePath,
      header: {
        'X-WX-SERVICE': SERVICE_NAME,
        'content-type': 'application/json',
      },
      method,
      data,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data);
        } else {
          console.error('Django 返回錯誤:', res.statusCode, res.data);
          resolve({
            success: false,
            error: (res.data && res.data.error) || '伺服器異常',
            statusCode: res.statusCode
          });
        }
      },
      fail(err) {
        console.error('雲托管調用失敗:', err);
        wx.showModal({
          title: '連線失敗',
          content: `請確認網路狀態\nPath: ${safePath}\nErr: ${err.errMsg}`,
          showCancel: false
        });
        reject(err);
      }
    });
  });
}

function request(path, method = 'GET', data = {}) {
  if (ENV === 'local') {
    return requestLocal(path, method, data);
  } else {
    return requestCloud(path, method, data);
  }
}

module.exports = { request, BASE_URL };
