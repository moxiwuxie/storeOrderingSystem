"""ORM 模型：与数据库表一一对应。"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# SQLite 仅支持 INTEGER PRIMARY KEY 自增，用变体兼容 MySQL 的 BIGINT
BigIntType = BigInteger().with_variant(Integer, "sqlite")


class User(Base):
    """用户表：支持微信 / 支付宝两种身份。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    openid: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    alipay_user_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    # H5（浏览器/支付宝内打开）端的设备标识，用于免注册识别同一顾客
    device_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    nickname: Mapped[str] = mapped_column(String(64), default="微信用户")
    avatar: Mapped[str] = mapped_column(String(512), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Admin(Base):
    """商家后台账号表。"""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    real_name: Mapped[str] = mapped_column(String(64), default="管理员")
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Category(Base):
    """商品分类。"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    """商品表。status: 1 上架 / 0 下架。"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(BigIntType, ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    image: Mapped[str] = mapped_column(String(512), default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)  # 无规格时的售价
    stock: Mapped[int] = mapped_column(Integer, default=0)  # 无规格时的库存
    unit: Mapped[str] = mapped_column(String(16), default="份")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    category: Mapped["Category"] = relationship(back_populates="products")
    specs: Mapped[list["ProductSpec"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductSpec(Base):
    """商品规格：如 大杯/中杯、加辣/不辣。一个商品可多条。"""

    __tablename__ = "product_specs"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(BigIntType, ForeignKey("products.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship(back_populates="specs")


class CartItem(Base):
    """购物车。spec_id 为空表示无规格商品。"""

    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "product_id", "spec_id", name="uq_cart_item"),)

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigIntType, ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(BigIntType, ForeignKey("products.id"))
    spec_id: Mapped[int | None] = mapped_column(BigIntType, ForeignKey("product_specs.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Order(Base):
    """订单主表。status: 0 待支付 / 1 已支付 / 2 已完成 / 3 已取消。"""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigIntType, ForeignKey("users.id"), index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    pay_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[int] = mapped_column(Integer, default=0)
    pay_type: Mapped[str] = mapped_column(String(16), default="")  # wechat / alipay
    transaction_id: Mapped[str] = mapped_column(String(64), default="")
    table_no: Mapped[str] = mapped_column(String(32), default="")
    remark: Mapped[str] = mapped_column(String(255), default="")
    pay_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """订单明细（下单时快照商品名、规格、单价）。"""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(BigIntType, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigIntType, ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(BigIntType)
    product_name: Mapped[str] = mapped_column(String(128))
    product_image: Mapped[str] = mapped_column(String(512), default="")
    spec_id: Mapped[int | None] = mapped_column(BigIntType, nullable=True)
    spec_name: Mapped[str] = mapped_column(String(64), default="")
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    order: Mapped["Order"] = relationship(back_populates="items")


# 订单状态常量
ORDER_STATUS_PENDING = 0
ORDER_STATUS_PAID = 1
ORDER_STATUS_FINISHED = 2
ORDER_STATUS_CANCELED = 3

ORDER_STATUS_TEXT = {
    ORDER_STATUS_PENDING: "待支付",
    ORDER_STATUS_PAID: "已支付",
    ORDER_STATUS_FINISHED: "已完成",
    ORDER_STATUS_CANCELED: "已取消",
}
