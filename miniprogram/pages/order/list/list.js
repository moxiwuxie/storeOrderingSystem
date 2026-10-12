const { request } = require('../../../utils/request');
const { formatTime } = require('../../../utils/util');

const TABS = [
  { label: '全部', status: null },
  { label: '待支付', status: 0 },
  { label: '已支付', status: 1 },
  { label: '已完成', status: 2 },
  { label: '已取消', status: 3 }
];

Page({
  data: {
    tabs: TABS,
    activeIndex: 0,
    orders: [],
    loading: true
  },

  onLoad(options) {
    if (options.status !== undefined && options.status !== '') {
      const index = TABS.findIndex((t) => t.status === Number(options.status));
      if (index >= 0) this.setData({ activeIndex: index });
    }
    this.load();
  },

  onShow() {
    if (!this.data.loading) this.load();
  },

  onTabChange(e) {
    this.setData({ activeIndex: Number(e.currentTarget.dataset.index) }, () => this.load());
  },

  onPullDownRefresh() {
    this.load().then(() => wx.stopPullDownRefresh());
  },

  load() {
    const tab = this.data.tabs[this.data.activeIndex];
    const url = tab.status === null ? '/api/orders' : '/api/orders?status=' + tab.status;
    return request({ url })
      .then((orders) => {
        this.setData({
          orders: (orders || []).map((o) => ({ ...o, created_text: formatTime(o.created_at) })),
          loading: false
        });
      })
      .catch(() => this.setData({ loading: false }));
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/order/detail/detail?order_no=' + e.currentTarget.dataset.no });
  },

  goMenu() {
    wx.switchTab({ url: '/pages/index/index' });
  }
});
