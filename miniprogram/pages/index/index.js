const { request } = require('../../utils/request');

Page({
  data: {
    categories: [],
    currentId: 0,
    scrollIntoId: '',
    cart: { items: [], total_quantity: 0, total_amount: 0 },
    // 规格弹窗
    showSpec: false,
    current: null,
    selectedSpecId: null,
    specQty: 1,
    loading: true
  },

  onLoad() {
    const app = getApp();
    const ready = app.globalData.loginReady || Promise.resolve();
    ready.then(() => this.loadAll());
  },

  onShow() {
    if (this.data.categories.length) this.loadCart();
  },

  async loadAll() {
    try {
      const categories = await request({ url: '/api/products/categories' });
      const list = (categories || []).filter((c) => c.products.length > 0);
      this.setData({
        categories: list,
        currentId: list.length ? list[0].id : 0,
        loading: false
      });
      await this.loadCart();
    } catch (e) {
      this.setData({ loading: false });
    }
  },

  async loadCart() {
    try {
      const cart = await request({ url: '/api/cart' });
      this.setData({ cart });
    } catch (e) {
      /* 未登录等场景忽略 */
    }
  },

  onSelectCategory(e) {
    const id = e.currentTarget.dataset.id;
    this.setData({ currentId: id, scrollIntoId: 'cat-' + id });
  },

  /** 点击商品：有规格弹窗选择，无规格直接加购 */
  onTapProduct(e) {
    const product = e.currentTarget.dataset.product;
    if (product.stock <= 0) {
      wx.showToast({ title: '该商品已售罄', icon: 'none' });
      return;
    }
    if (product.specs && product.specs.length) {
      const first = product.specs.find((s) => s.stock > 0) || product.specs[0];
      this.setData({ showSpec: true, current: product, selectedSpecId: first.id, specQty: 1 });
    } else {
      this.addToCart(product.id, null, 1);
    }
  },

  onSelectSpec(e) {
    this.setData({ selectedSpecId: e.currentTarget.dataset.id });
  },

  onSpecQtyChange(e) {
    const delta = Number(e.currentTarget.dataset.delta);
    const qty = Math.max(1, this.data.specQty + delta);
    this.setData({ specQty: qty });
  },

  onCloseSpec() {
    this.setData({ showSpec: false });
  },

  onConfirmSpec() {
    const { current, selectedSpecId, specQty } = this.data;
    this.addToCart(current.id, selectedSpecId, specQty).then(() => {
      this.setData({ showSpec: false });
    });
  },

  addToCart(productId, specId, quantity) {
    return request({
      url: '/api/cart',
      method: 'POST',
      data: { product_id: productId, spec_id: specId, quantity },
      showLoading: true
    })
      .then((cart) => {
        this.setData({ cart });
        wx.showToast({ title: '已加入购物车', icon: 'success' });
      })
      .catch(() => {});
  },

  goCart() {
    wx.switchTab({ url: '/pages/cart/cart' });
  },

  goCheckout() {
    if (!this.data.cart.total_quantity) return;
    wx.navigateTo({ url: '/pages/order/confirm/confirm' });
  }
});
