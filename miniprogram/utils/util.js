function formatTime(input) {
  if (!input) return '';
  const date = typeof input === 'string' ? new Date(input.replace(/-/g, '/')) : new Date(input);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n) => (n < 10 ? '0' + n : '' + n);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function money(value) {
  return Number(value || 0).toFixed(2);
}

// 订单状态色值，供页面复用
const ORDER_STATUS_COLOR = {
  0: '#ff6b35',
  1: '#1890ff',
  2: '#52c41a',
  3: '#999999'
};

module.exports = { formatTime, money, ORDER_STATUS_COLOR };
