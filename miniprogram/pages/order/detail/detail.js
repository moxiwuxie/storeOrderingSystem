const { request } = require('../../../utils/request');
const { formatTime } = require('../../../utils/util');

Page({
  data: {
    order: null,
    created_text: '',
    pay_text: '',
    paying: false
  },

  onLoad(options) {
    this.orderNo = options.order_no;
  },

  onShow() {
    this.load();
  },

  load() {
    return request({ url: '/api/orders/' + this.orderNo })
      .then((order) => {
        this.setData({
          order,
          created_text: formatTime(order.created_at),
          pay_text: formatTime(order.pay_time)
        });
      })
      .catch(() => {});
  },

  onPay() {
    if (this.data.paying) return;
    this.setData({ paying: true });
    wx.showActionSheet({
      itemList: ['微信支付', '支付宝支付'],
      success: (res) => this.pay(res.tapIndex === 0 ? 'wechat' : 'alipay'),
      fail: () => this.setData({ paying: false })
    });
  },

  pay(payType) {
    request({
      url: '/api/payment/prepay',
      method: 'POST',
      data: { order_no: this.orderNo, pay_type: payType },
      showLoading: true
    })
      .then((res) => {
        if (res.mock || res.paid) {
          wx.redirectTo({ url: `/pages/pay-result/pay-result?order_no=${this.orderNo}&success=1` });
          return;
        }
        if (payType === 'wechat') {
          wx.requestPayment({
            ...res.pay_params,
            success: () => wx.redirectTo({ url: `/pages/pay-result/pay-result?order_no=${this.orderNo}&success=1` }),
            fail: () => wx.redirectTo({ url: `/pages/pay-result/pay-result?order_no=${this.orderNo}&success=0` })
          });
        }
      })
      .catch(() => {})
      .finally(() => this.setData({ paying: false }));
  },

  onCancel() {
    wx.showModal({
      title: '提示',
      content: '确定要取消该订单吗？',
      success: (res) => {
        if (!res.confirm) return;
        request({ url: `/api/orders/${this.orderNo}/cancel`, method: 'POST' })
          .then(() => {
            wx.showToast({ title: '已取消', icon: 'success' });
            this.load();
          })
          .catch(() => {});
      }
    });
  }
});
