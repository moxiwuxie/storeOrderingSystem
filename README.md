# 门店扫码点单系统

面向到店顾客的线上自助点单系统：顾客扫码进入点单页 → 浏览商品 → 加购 → 下单 → 线上支付 → 查看订单；商家通过后台管理商品、库存与订单。

## 多端支持

同一套后端接口同时服务三个入口，业务逻辑与数据库完全复用：

| 入口 | 打开方式 | 登录方式 | 支付方式 |
|---|---|---|---|
| **微信小程序** | 微信扫码 / 小程序搜索 | `wx.login` 静默授权 | 微信支付 JSAPI |
| **H5 点单页（支付宝）** | 支付宝扫码 / 支付宝内打开 `/h5/` | 支付宝授权 → 设备标识免注册 | 支付宝手机网站支付 |
| **H5 点单页（浏览器）** | 手机/电脑浏览器打开 `/h5/` | 设备标识免注册（可选绑手机号） | 微信 H5 支付 / 支付宝 H5 |

- 小程序源码：[miniprogram/](file:///Users/xiaoxu/Desktop/PycharmProjects/storeOrderingSystem/miniprogram)
- H5 点单页：[backend/static/h5/index.html](file:///Users/xiaoxu/Desktop/PycharmProjects/storeOrderingSystem/backend/static/h5/index.html)（由后端直接托管，访问 `/h5/` 即为可用点单页）
- 商家后台：[backend/static/admin/index.html](file:///Users/xiaoxu/Desktop/PycharmProjects/storeOrderingSystem/backend/static/admin/index.html)

支付按「渠道 × 来源端」自动分流：小程序来源返回 JSAPI 参数，H5 来源返回网页跳转地址或表单，前端只需按返回的 `mode` 处理。

## 目录结构

```
storeOrderingSystem/
├── backend/                    # 后端服务（FastAPI + SQLAlchemy）
│   ├── app/
│   │   ├── main.py             # 应用入口、路由注册、初始化数据
│   │   ├── config.py           # 配置（读 .env）
│   │   ├── database.py         # 数据库引擎与会话
│   │   ├── models.py           # ORM 模型（9 张表）
│   │   ├── schemas.py          # 请求/响应结构
│   │   ├── security.py         # 密码哈希 + JWT
│   │   ├── deps.py             # 登录态依赖（用户 / 管理员）
│   │   ├── services/
│   │   │   └── third_party.py  # 微信登录 / 支付宝登录 / 支付封装
│   │   └── routers/
│   │       ├── auth.py         # 登录模块
│   │       ├── products.py     # 商品展示模块
│   │       ├── cart.py         # 购物车模块
│   │       ├── orders.py       # 下单 + 订单模块
│   │       ├── payment.py      # 支付模块 + 支付回调
│   │       └── admin.py        # 后台管理端
│   ├── static/admin/index.html # 商家后台网页
│   ├── static/h5/index.html    # H5 点单页（浏览器 / 支付宝内打开）
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py                  # 本地启动脚本
├── miniprogram/                # 微信小程序前端（原生）
│   ├── app.js / app.json / app.wxss
│   ├── config.js               # 后端地址配置
│   ├── utils/request.js        # 请求封装（token / 错误处理）
│   └── pages/
│       ├── index/              # 点单（分类 + 商品 + 规格弹窗 + 购物车条）
│       ├── cart/               # 购物车
│       ├── order/confirm/      # 确认订单
│       ├── order/list/         # 我的订单（按状态筛选）
│       ├── order/detail/       # 订单详情
│       ├── user/               # 个人中心（微信/支付宝登录）
│       └── pay-result/         # 支付结果
├── sql/mysql_schema.sql        # MySQL 建表脚本
└── docs/
    ├── 部署文档.md
    ├── 数据库设计.md
    └── 接口文档.md
```

## 快速开始（本地）

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 默认 SQLite，零配置即可运行
python run.py                 # 启动在 http://127.0.0.1:8000
```

- 接口文档（Swagger）：<http://127.0.0.1:8000/docs>
- 商家后台：<http://127.0.0.1:8000/admin/>（默认 `admin` / `admin123`）
- **H5 点单页**：<http://127.0.0.1:8000/h5/>（浏览器直接打开即可点单，也可用手机访问）
- 首次启动自动建表并写入演示分类/商品

### 2. 启动小程序

1. 微信开发者工具 → 导入项目 → 选择 `miniprogram/` 目录
2. 修改 [config.js](file:///Users/xiaoxu/Desktop/PycharmProjects/storeOrderingSystem/miniprogram/config.js) 中的 `baseUrl`：
   - 模拟器调试：`http://127.0.0.1:8000`
   - 真机预览：改成电脑局域网 IP，如 `http://192.168.1.10:8000`
3. 详情 → 本地设置 → 勾选「不校验合法域名、web-view、TLS 版本以及 HTTPS 证书」
4. 编译运行即可点单

### 3. 打开 H5 点单页

无需任何构建，后端启动后即可访问：

```bash
# 电脑浏览器
open http://127.0.0.1:8000/h5/

# 手机同局域网访问（把 IP 换成电脑局域网 IP）
# http://192.168.1.10:8000/h5/
```

页面会自动识别运行环境：在支付宝客户端内打开时优先推荐支付宝支付，在微信内打开时推荐微信支付，普通浏览器则两者皆可。首次进入自动生成设备标识完成免注册登录。

## 核心接口一览

| 模块 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 登录 | POST | `/api/auth/wechat` | 微信 code 换 token（小程序）|
| 登录 | POST | `/api/auth/alipay` | 支付宝 auth_code 换 token（小程序）|
| 登录 | POST | `/api/auth/h5` | H5 免注册登录（设备标识 / 支付宝授权码 / 手机号）|
| 商品 | GET | `/api/products/categories` | 分类 + 在售商品 |
| 商品 | GET | `/api/products/{id}` | 商品详情 |
| 购物车 | GET/POST | `/api/cart` | 查看 / 加入购物车 |
| 购物车 | PUT/DELETE | `/api/cart/{id}` | 改数量 / 删除 |
| 下单 | POST | `/api/orders` | 生成订单并校验扣减库存 |
| 订单 | GET | `/api/orders?status=` | 我的订单 |
| 订单 | POST | `/api/orders/{no}/cancel` | 取消待支付订单 |
| 支付 | POST | `/api/payment/prepay` | 发起支付（按 `source` 分流小程序 / H5）|
| 支付 | POST | `/api/payment/wechat/notify` | 微信回调 |
| 支付 | POST | `/api/payment/alipay/notify` | 支付宝回调 |
| 后台 | POST | `/api/admin/login` | 管理员登录 |
| 后台 | GET/POST/PUT/DELETE | `/api/admin/products` | 商品与库存维护 |
| 后台 | GET/PUT | `/api/admin/orders` | 订单查看与状态管理 |
| 后台 | GET | `/api/admin/stats` | 数据统计 |

完整字段见 [接口文档.md](file:///Users/xiaoxu/Desktop/PycharmProjects/storeOrderingSystem/docs/接口文档.md)。

## 数据安全

- 用户 / 管理员均使用 JWT 鉴权，小程序端仅存储 token，不存敏感信息
- 订单、购物车接口一律按 `user_id` 过滤，杜绝越权访问他人订单
- 管理端接口独立鉴权（`role=admin`），与用户端隔离
- 管理员密码使用 PBKDF2-SHA256 加盐哈希存储

## 支付说明

默认 `PAY_MODE=mock`：本地点击支付即视为成功，便于全流程联调。

支付接口按「渠道 × 来源端」分流，请求体中的 `source` 决定返回形态：

| pay_type | source | 返回 `mode` | 前端处理 |
|---|---|---|---|
| `wechat` | `miniprogram` | `jsapi` | `wx.requestPayment(pay_params)` |
| `wechat` | `h5` | `h5_redirect` | `location.href = pay_params.h5_url` |
| `alipay` | `miniprogram` | `order_str` | `my.tradePay({ orderStr })` |
| `alipay` | `h5` | `h5_form` | 把 `pay_params.form_html` 注入并提交表单 |

上线前将 `PAY_MODE` 改为 `real`，并在 [third_party.py](file:///Users/xiaoxu/Desktop/PycharmProjects/storeOrderingSystem/backend/app/services/third_party.py) 中补齐微信支付 v3 / 支付宝的签名、验签与回调解密（文件中已标注 TODO 位置）。详见 [部署文档.md](file:///Users/xiaoxu/Desktop/PycharmProjects/storeOrderingSystem/docs/部署文档.md)。
