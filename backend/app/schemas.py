"""请求/响应数据结构（Pydantic Schema）。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- 通用 ----------
class Resp(BaseModel):
    code: int = 0
    msg: str = "ok"
    data: object | None = None


# ---------- 登录 ----------
class WechatLoginIn(BaseModel):
    code: str = Field(..., description="wx.login 获取的 code")
    nickname: str | None = None
    avatar: str | None = None


class AlipayLoginIn(BaseModel):
    auth_code: str = Field(..., description="支付宝授权 auth_code")
    nickname: str | None = None
    avatar: str | None = None


class H5LoginIn(BaseModel):
    """H5（浏览器 / 支付宝内打开）登录：设备标识免注册识别，可选带支付宝授权码。"""

    device_id: str = Field(..., min_length=8, description="前端生成并持久化的设备标识")
    auth_code: str | None = Field(None, description="支付宝授权码，配置后可换取真实 alipay_user_id")
    phone: str | None = Field(None, description="手机号，选填，用于跨设备找回订单")
    nickname: str | None = None
    avatar: str | None = None


class LoginOut(BaseModel):
    token: str
    user_id: int
    nickname: str
    avatar: str


class AdminLoginIn(BaseModel):
    username: str
    password: str


# ---------- 商品 ----------
class SpecOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: float
    stock: int


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int
    name: str
    description: str
    image: str
    price: float
    stock: int
    unit: str
    status: bool
    specs: list[SpecOut] = []


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    sort: int
    products: list[ProductOut] = []


# ---------- 购物车 ----------
class CartAddIn(BaseModel):
    product_id: int
    spec_id: int | None = None
    quantity: int = Field(1, ge=1)


class CartUpdateIn(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemOut(BaseModel):
    id: int
    product_id: int
    spec_id: int | None
    name: str
    spec_name: str
    image: str
    price: float
    quantity: int
    stock: int
    subtotal: float


class CartOut(BaseModel):
    items: list[CartItemOut]
    total_quantity: int
    total_amount: float


# ---------- 订单 ----------
class OrderCreateIn(BaseModel):
    remark: str = ""
    table_no: str = ""


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    product_name: str
    product_image: str
    spec_name: str
    price: float
    quantity: int
    subtotal: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    total_amount: float
    pay_amount: float
    status: int
    status_text: str = ""
    pay_type: str
    table_no: str
    remark: str
    pay_time: datetime | None
    created_at: datetime
    items: list[OrderItemOut] = []


class PayIn(BaseModel):
    order_no: str
    pay_type: str = Field(..., pattern="^(wechat|alipay)$")
    # 支付来源端：miniprogram=微信小程序 JSAPI；h5=浏览器/支付宝内打开的 H5
    source: str = Field("miniprogram", pattern="^(miniprogram|h5)$")


class PayOut(BaseModel):
    order_no: str
    pay_type: str
    mock: bool
    # mock 模式下直接返回支付成功；real 模式返回拉起支付所需参数
    pay_params: dict = {}
    paid: bool = False


# ---------- 管理端 ----------
class AdminProductIn(BaseModel):
    category_id: int
    name: str
    description: str = ""
    image: str = ""
    price: float = 0
    stock: int = 0
    unit: str = "份"
    sort: int = 0
    status: bool = True


class AdminSpecIn(BaseModel):
    id: int | None = None
    name: str
    price: float
    stock: int = 0
    sort: int = 0


class AdminProductSpecIn(AdminProductIn):
    specs: list[AdminSpecIn] = []


class AdminCategoryIn(BaseModel):
    name: str
    sort: int = 0
    status: bool = True


class StockUpdateIn(BaseModel):
    stock: int = Field(..., ge=0)


class OrderStatusIn(BaseModel):
    status: int = Field(..., ge=0, le=3)
