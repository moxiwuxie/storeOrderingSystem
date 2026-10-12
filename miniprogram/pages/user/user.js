const { request, getToken } = require('../../utils/request');

Page({
  data: {
    userInfo: null,
    orderCount: 0
  },

  onShow() {
    const app = getApp();
    if (!getToken()) {
      app.login().then(() => this.loadProfile());
    } else {
      this.loadProfile();
    }
  },

  loadProfile() {
    request({ url: '/api/auth/profile' })
      .then((userInfo) => this.setData({ userInfo }))
      .catch(() => {});
    request({ url: '/api/orders' })
      .then((orders) => this.setData({ orderCount: (orders || []).length }))
      .catch(() => {});
  },

  /** 支付宝扫码登录：真实场景由扫码后携带 auth_code 进入 */
  onAlipayLogin() {
    const app = getApp();
    app
      .alipayLogin('alipay_scan_' + Date.now())
      .then((data) => {
        this.setData({ userInfo: data });
        wx.showToast({ title: '支付宝登录成功', icon: 'success' });
        this.loadProfile();
      })
      .catch(() => {});
  },

  onWechatLogin() {
    const app = getApp();
    app.globalData.userInfo = null;
    app.login().then(() => this.loadProfile());
  },

  goOrders(e) {
    const status = e.currentTarget.dataset.status;
    const query = status === undefined || status === '' ? '' : '?status=' + status;
    wx.navigateTo({ url: '/pages/order/list/list' + query });
  },

  onLogout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (!res.confirm) return;
        getApp().logout();
        this.setData({ userInfo: null, orderCount: 0 });
      }
    });
  }
});
