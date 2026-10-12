const { request } = require('../../utils/request');

Page({
  data: {
    success: true,
    orderNo: '',
    order: null
  },

  onLoad(options) {
    const success = options.success === '1';
    this.setData({ success, orderNo: options.order_no || '' });
    this.refresh();
  },

  async refresh() {
    try {
      const order = await request({ url: '/api/orders/' + this.data.orderNo });
      // 以服务端状态为准（支付回调可能稍后到达）
      this.setData({ order, success: order.status === 1 || order.status === 2 });
    } catch (e) {
      /* ignore */
    }
  },

  goOrders() {
    wx.redirectTo({ url: '/pages/order/list/list' });
  },

  goMenu() {
    wx.switchTab({ url: '/pages/index/index' });
  }
});
