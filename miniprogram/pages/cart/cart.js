const { request } = require('../../utils/request');

Page({
  data: {
    cart: { items: [], total_quantity: 0, total_amount: 0 },
    loading: true
  },

  onShow() {
    this.loadCart();
  },

  async loadCart() {
    try {
      const cart = await request({ url: '/api/cart' });
      this.setData({ cart, loading: false });
    } catch (e) {
      this.setData({ loading: false });
    }
  },

  changeQty(e) {
    const { id, delta } = e.currentTarget.dataset;
    const item = this.data.cart.items.find((i) => i.id === id);
    if (!item) return;
    const quantity = item.quantity + Number(delta);
    if (quantity <= 0) {
      this.remove(id);
      return;
    }
    if (quantity > item.stock) {
      wx.showToast({ title: '已达库存上限', icon: 'none' });
      return;
    }
    request({ url: '/api/cart/' + id, method: 'PUT', data: { quantity } })
      .then((cart) => this.setData({ cart }))
      .catch(() => {});
  },

  remove(id) {
    wx.showModal({
      title: '提示',
      content: '确定要移除该商品吗？',
      success: (res) => {
        if (!res.confirm) return;
        request({ url: '/api/cart/' + id, method: 'DELETE' })
          .then((cart) => this.setData({ cart }))
          .catch(() => {});
      }
    });
  },

  clearCart() {
    if (!this.data.cart.items.length) return;
    wx.showModal({
      title: '提示',
      content: '确定要清空购物车吗？',
      success: (res) => {
        if (!res.confirm) return;
        request({ url: '/api/cart', method: 'DELETE' })
          .then((cart) => this.setData({ cart }))
          .catch(() => {});
      }
    });
  },

  goMenu() {
    wx.switchTab({ url: '/pages/index/index' });
  },

  goCheckout() {
    if (!this.data.cart.total_quantity) return;
    wx.navigateTo({ url: '/pages/order/confirm/confirm' });
  }
});
