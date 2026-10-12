"""购物车模块：增删改数量、合计金额。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CartItem, Product, ProductSpec, User
from ..schemas import CartAddIn, CartUpdateIn, Resp

router = APIRouter(prefix="/api/cart", tags=["购物车"])


def _resolve_price_stock(product: Product, spec: ProductSpec | None) -> tuple[float, int]:
    if spec is not None:
        return float(spec.price), spec.stock
    return float(product.price), product.stock


def _build_cart(db: Session, user: User) -> dict:
    items = (
        db.query(CartItem)
        .filter(CartItem.user_id == user.id)
        .order_by(CartItem.id.asc())
        .all()
    )
    result, total_qty, total_amount = [], 0, 0.0
    valid_ids = []
    for item in items:
        product = db.get(Product, item.product_id)
        spec = db.get(ProductSpec, item.spec_id) if item.spec_id else None
        if not product or not product.status or (item.spec_id and not spec):
            valid_ids.append(item.id)  # 商品下架/规格删除视为失效，自动清理
            continue
        price, stock = _resolve_price_stock(product, spec)
        subtotal = round(price * item.quantity, 2)
        total_qty += item.quantity
        total_amount += subtotal
        result.append(
            {
                "id": item.id,
                "product_id": product.id,
                "spec_id": item.spec_id,
                "name": product.name,
                "spec_name": spec.name if spec else "",
                "image": product.image,
                "price": price,
                "quantity": item.quantity,
                "stock": stock,
                "subtotal": subtotal,
            }
        )
    if valid_ids:
        db.query(CartItem).filter(CartItem.id.in_(valid_ids)).delete(synchronize_session=False)
        db.commit()
    return {"items": result, "total_quantity": total_qty, "total_amount": round(total_amount, 2)}


@router.get("", response_model=Resp)
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return Resp(data=_build_cart(db, user))


@router.post("", response_model=Resp)
def add_to_cart(payload: CartAddIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, payload.product_id)
    if not product or not product.status:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")

    spec = None
    if payload.spec_id:
        spec = db.get(ProductSpec, payload.spec_id)
        if not spec or spec.product_id != product.id:
            raise HTTPException(status_code=400, detail="规格不存在")

    _, stock = _resolve_price_stock(product, spec)

    item = (
        db.query(CartItem)
        .filter(
            CartItem.user_id == user.id,
            CartItem.product_id == product.id,
            CartItem.spec_id == payload.spec_id,
        )
        .first()
    )
    target_qty = (item.quantity if item else 0) + payload.quantity
    if target_qty > stock:
        raise HTTPException(status_code=400, detail=f"库存不足，当前仅剩 {stock} {product.unit}")

    if item:
        item.quantity = target_qty
    else:
        db.add(
            CartItem(
                user_id=user.id,
                product_id=product.id,
                spec_id=payload.spec_id,
                quantity=payload.quantity,
            )
        )
    db.commit()
    return Resp(data=_build_cart(db, user))


@router.put("/{item_id}", response_model=Resp)
def update_quantity(
    item_id: int,
    payload: CartUpdateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="购物车项不存在")

    product = db.get(Product, item.product_id)
    spec = db.get(ProductSpec, item.spec_id) if item.spec_id else None
    _, stock = _resolve_price_stock(product, spec)
    if payload.quantity > stock:
        raise HTTPException(status_code=400, detail=f"库存不足，当前仅剩 {stock}")
    item.quantity = payload.quantity
    db.commit()
    return Resp(data=_build_cart(db, user))


@router.delete("/{item_id}", response_model=Resp)
def remove_item(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(CartItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    db.delete(item)
    db.commit()
    return Resp(data=_build_cart(db, user))


@router.delete("", response_model=Resp)
def clear_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(CartItem).filter(CartItem.user_id == user.id).delete(synchronize_session=False)
    db.commit()
    return Resp(data={"items": [], "total_quantity": 0, "total_amount": 0.0})
