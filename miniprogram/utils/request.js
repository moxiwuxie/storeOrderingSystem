const config = require('./config');

const TOKEN_KEY = 'token';

function getToken() {
  return wx.getStorageSync(TOKEN_KEY) || '';
}

function setToken(token) {
  wx.setStorageSync(TOKEN_KEY, token);
}

function clearToken() {
  wx.removeStorageSync(TOKEN_KEY);
}

/**
 * 统一请求封装：
 * - 自动携带 token
 * - code !== 0 统一 toast
 * - 401 清理登录态并触发重新登录
 */
function request(options) {
  const { url, method = 'GET', data = {}, showLoading = false, auth = true } = options;

  if (showLoading) wx.showLoading({ title: '加载中', mask: true });

  return new Promise((resolve, reject) => {
    wx.request({
      url: config.baseUrl + url,
      method,
      data,
      header: Object.assign(
        { 'content-type': 'application/json' },
        auth && getToken() ? { Authorization: 'Bearer ' + getToken() } : {}
      ),
      success(res) {
        const body = res.data || {};
        if (res.statusCode === 401) {
          clearToken();
          const app = getApp();
          if (app && app.login) app.login();
          reject(new Error(body.msg || '登录已过期'));
          return;
        }
        if (body.code === 0) {
          resolve(body.data);
        } else {
          wx.showToast({ title: body.msg || '请求失败', icon: 'none' });
          reject(new Error(body.msg || '请求失败'));
        }
      },
      fail(err) {
        wx.showToast({ title: '网络异常，请检查服务是否启动', icon: 'none' });
        reject(err);
      },
      complete() {
        if (showLoading) wx.hideLoading();
      }
    });
  });
}

module.exports = { request, getToken, setToken, clearToken };
