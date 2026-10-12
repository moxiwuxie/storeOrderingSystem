"""下单模块 + 订单模块：确认订单、生成订单编号、查询历史订单、取消订单。"""
import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_PENDING,
    ORDER_STATUS_TEXT,
    CartItem,
    Order,
    OrderItem,
    Product,
    ProductSpec,
    User,
)
from ..schemas import OrderCreateIn, Resp

router = APIRouter(prefix="/api/orders", tags=["订单"])


def generate_order_no() -> str:
    """订单编号：SO + yyyyMMddHHmmss + 4 位随机数。"""
    return f"SO{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def order_to_dict(order: Order) -> dict:
    return {
        "id": order.id,
        "order_no": order.order_no,
        "total_amount": float(order.total_amount),
        "pay_amount": float(order.pay_amount),
        "status": order.status,
        "status_text": ORDER_STATUS_TEXT.get(order.status, "未知"),
        "pay_type": order.pay_type,
        "table_no": order.table_no,
        "remark": order.remark,
        "pay_time": order.pay_time,
        "created_at": order.created_at,
        "items": [
            {
                "product_id": i.product_id,
                "product_name": i.product_name,
                "product_image": i.product_image,
                "spec_name": i.spec_name,
                "price": float(i.price),
                "quantity": i.quantity,
                "subtotal": float(i.subtotal),
            }
            for i in order.items
        ],
    }


@router.post("", response_model=Resp)
def create_order(payload: OrderCreateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """由购物车生成订单，下单同时校验并扣减库存（库存不足直接失败）。"""
    cart_items = db.query(CartItem).filter(CartItem.user_id == user.id).order_by(CartItem.id.asc()).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="购物车为空，无法下单")

    order = Order(
        order_no=generate_order_no(),
        user_id=user.id,
        status=ORDER_STATUS_PENDING,
        table_no=payload.table_no,
        remark=payload.remark,
        total_amount=0,
        pay_amount=0,
    )
    db.add(order)
    db.flush()  # 先拿到 order.id

    total = 0.0
    try:
        for cart_item in cart_items:
            product = db.get(Product, cart_item.product_id)
            if not product or not product.status:
                raise HTTPException(status_code=400, detail="商品已下架，请重新选择")

            spec = db.get(ProductSpec, cart_item.spec_id) if cart_item.spec_id else None
            if cart_item.spec_id and not spec:
                raise HTTPException(status_code=400, detail="商品规格已变更，请重新选择")

            price = float(spec.price) if spec else float(product.price)
            stock = spec.stock if spec else product.stock
            if cart_item.quantity > stock:
                raise HTTPException(
                    status_code=400,
                    detail=f"「{product.name}」库存不足，仅剩 {stock} {product.unit}",
                )

            # 扣减库存
            if spec:
                spec.stock -= cart_item.quantity
            else:
                product.stock -= cart_item.quantity

            subtotal = round(price * cart_item.quantity, 2)
            total += subtotal
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_image=product.image,
                    spec_id=spec.id if spec else None,
                    spec_name=spec.name if spec else "",
                    price=price,
                    quantity=cart_item.quantity,
                    subtotal=subtotal,
                )
            )

        order.total_amount = round(total, 2)
        order.pay_amount = round(total, 2)

        # 清空购物车
        db.query(CartItem).filter(CartItem.user_id == user.id).delete(synchronize_session=False)
        db.commit()
    except HTTPException:
        db.rollback()
        raise

    db.refresh(order)
    return Resp(data=order_to_dict(order))


@router.get("", response_model=Resp)
def list_orders(status: int | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """我的订单列表，可按状态过滤。"""
    query = (
        db.query(Order)
        .filter(Order.user_id == user.id)
        .options(selectinload(Order.items))
        .order_by(Order.id.desc())
    )
    if status is not None:
        query = query.filter(Order.status == status)
    return Resp(data=[order_to_dict(o) for o in query.all()])


@router.get("/{order_no}", response_model=Resp)
def order_detail(order_no: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .filter(Order.order_no == order_no, Order.user_id == user.id)
        .options(selectinload(Order.items))
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return Resp(data=order_to_dict(order))


@router.post("/{order_no}/cancel", response_model=Resp)
def cancel_order(order_no: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """取消待支付订单，并回滚库存。"""
    order = (
        db.query(Order)
        .filter(Order.order_no == order_no, Order.user_id == user.id)
        .options(selectinload(Order.items))
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != ORDER_STATUS_PENDING:
        raise HTTPException(status_code=400, detail="仅待支付订单可取消")

    for item in order.items:
        if item.spec_id:
            spec = db.get(ProductSpec, item.spec_id)
            if spec:
                spec.stock += item.quantity
        else:
            product = db.get(Product, item.product_id)
            if product:
                product.stock += item.quantity
    order.status = ORDER_STATUS_CANCELED
    db.commit()
    db.refresh(order)
    return Resp(data=order_to_dict(order))
