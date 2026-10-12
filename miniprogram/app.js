const { request, setToken, clearToken, getToken } = require('./utils/request');
const config = require('./config');

App({
  globalData: {
    userInfo: null,
    needTableNo: config.needTableNo,
    loginReady: null
  },

  onLaunch() {
    this.globalData.loginReady = this.login();
  },

  /**
   * 微信授权登录：wx.login 拿 code -> 后端换 openid -> 存 token。
   * 返回 Promise，页面可 await app.globalData.loginReady 保证已登录。
   */
  login() {
    if (this.globalData.userInfo && getToken()) {
      return Promise.resolve(this.globalData.userInfo);
    }
    return new Promise((resolve) => {
      wx.login({
        success: async (res) => {
          if (!res.code) return resolve(null);
          try {
            const data = await request({
              url: '/api/auth/wechat',
              method: 'POST',
              data: { code: res.code },
              auth: false
            });
            setToken(data.token);
            this.globalData.userInfo = data;
            resolve(data);
          } catch (e) {
            resolve(null);
          }
        },
        fail: () => resolve(null)
      });
    });
  },

  /** 支付宝扫码登录（扫码后带 auth_code 进入，或用户主动触发） */
  alipayLogin(authCode) {
    return request({
      url: '/api/auth/alipay',
      method: 'POST',
      data: { auth_code: authCode || 'alipay_scan_' + Date.now() },
      auth: false
    }).then((data) => {
      setToken(data.token);
      this.globalData.userInfo = data;
      return data;
    });
  },

  logout() {
    clearToken();
    this.globalData.userInfo = null;
  }
});
