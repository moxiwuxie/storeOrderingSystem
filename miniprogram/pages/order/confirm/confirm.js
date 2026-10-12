const { request } = require('../../../utils/request');
const config = require('../../../config');

Page({
  data: {
    cart: { items: [], total_quantity: 0, total_amount: 0 },
    remark: '',
    tableNo: '',
    needTableNo: config.needTableNo,
    submitting: false
  },

  onLoad() {
    this.loadCart();
  },

  async loadCart() {
    try {
      const cart = await request({ url: '/api/cart' });
      if (!cart.items.length) {
        wx.showToast({ title: '购物车为空', icon: 'none' });
        setTimeout(() => wx.navigateBack(), 800);
        return;
      }
      this.setData({ cart });
    } catch (e) {
      /* ignore */
    }
  },

  onRemarkInput(e) {
    this.setData({ remark: e.detail.value });
  },

  onTableInput(e) {
    this.setData({ tableNo: e.detail.value });
  },

  /** 提交订单 -> 选择支付方式 -> 拉起支付 */
  onSubmit() {
    if (this.data.submitting) return;
    if (this.data.needTableNo && !this.data.tableNo) {
      wx.showToast({ title: '请填写桌号', icon: 'none' });
      return;
    }
    this.setData({ submitting: true });

    request({
      url: '/api/orders',
      method: 'POST',
      data: { remark: this.data.remark, table_no: this.data.tableNo },
      showLoading: true
    })
      .then((order) => {
        wx.showActionSheet({
          itemList: ['微信支付', '支付宝支付'],
          success: (res) => this.pay(order.order_no, res.tapIndex === 0 ? 'wechat' : 'alipay'),
          fail: () => this.pay(order.order_no, 'wechat')
        });
      })
      .catch(() => {})
      .finally(() => this.setData({ submitting: false }));
  },

  pay(orderNo, payType) {
    request({
      url: '/api/payment/prepay',
      method: 'POST',
      data: { order_no: orderNo, pay_type: payType },
      showLoading: true
    })
      .then((res) => {
        if (res.mock || res.paid) {
          // 本地模拟支付：直接成功
          this.toResult(orderNo, true);
          return;
        }
        if (payType === 'wechat') {
          wx.requestPayment({
            ...res.pay_params,
            success: () => this.toResult(orderNo, true),
            fail: () => this.toResult(orderNo, false)
          });
        } else {
          // 支付宝：跳转收银台（真实环境由支付宝侧回跳）
          wx.showToast({ title: '请完成支付宝付款', icon: 'none' });
          this.toResult(orderNo, false);
        }
      })
      .catch(() => this.toResult(orderNo, false));
  },

  toResult(orderNo, success) {
    wx.redirectTo({ url: `/pages/pay-result/pay-result?order_no=${orderNo}&success=${success ? 1 : 0}` });
  }
});
