"""后台管理端（商家）：登录、分类/商品/规格/库存维护、订单管理、数据统计。"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_admin
from ..models import (
    ORDER_STATUS_FINISHED,
    ORDER_STATUS_PAID,
    ORDER_STATUS_TEXT,
    Admin,
    Category,
    Order,
    OrderItem,
    Product,
    ProductSpec,
)
from ..schemas import (
    AdminCategoryIn,
    AdminLoginIn,
    AdminProductSpecIn,
    OrderStatusIn,
    Resp,
    StockUpdateIn,
)
from ..security import create_token, verify_password
from .orders import order_to_dict

router = APIRouter(prefix="/api/admin", tags=["管理端"])


# ---------- 登录 ----------
@router.post("/login", response_model=Resp)
def admin_login(payload: AdminLoginIn, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.username == payload.username).first()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not admin.status:
        raise HTTPException(status_code=403, detail="账号已禁用")
    return Resp(data={"token": create_token(admin.id, "admin"), "real_name": admin.real_name})


# ---------- 分类 ----------
@router.get("/categories", response_model=Resp)
def admin_categories(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    categories = db.query(Category).order_by(Category.sort.asc(), Category.id.asc()).all()
    return Resp(
        data=[
            {"id": c.id, "name": c.name, "sort": c.sort, "status": c.status,
             "product_count": db.query(Product).filter(Product.category_id == c.id).count()}
            for c in categories
        ]
    )


@router.post("/categories", response_model=Resp)
def create_category(payload: AdminCategoryIn, db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return Resp(data={"id": category.id})


@router.put("/categories/{category_id}", response_model=Resp)
def update_category(
    category_id: int, payload: AdminCategoryIn, db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    for key, value in payload.model_dump().items():
        setattr(category, key, value)
    db.commit()
    return Resp()


@router.delete("/categories/{category_id}", response_model=Resp)
def delete_category(category_id: int, db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")
    if db.query(Product).filter(Product.category_id == category_id).count():
        raise HTTPException(status_code=400, detail="该分类下仍有商品，无法删除")
    db.delete(category)
    db.commit()
    return Resp()


# ---------- 商品 ----------
@router.get("/products", response_model=Resp)
def admin_products(
    category_id: int | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    query = db.query(Product).options(selectinload(Product.specs))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if keyword:
        query = query.filter(Product.name.like(f"%{keyword}%"))
    products = query.order_by(Product.sort.asc(), Product.id.desc()).all()
    return Resp(
        data=[
            {
                "id": p.id,
                "category_id": p.category_id,
                "name": p.name,
                "description": p.description,
                "image": p.image,
                "price": float(p.price),
                "stock": p.stock,
                "unit": p.unit,
                "sort": p.sort,
                "status": p.status,
                "specs": [
                    {"id": s.id, "name": s.name, "price": float(s.price), "stock": s.stock, "sort": s.sort}
                    for s in sorted(p.specs, key=lambda x: (x.sort, x.id))
                ],
            }
            for p in products
        ]
    )


@router.post("/products", response_model=Resp)
def create_product(
    payload: AdminProductSpecIn, db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)
):
    if not db.get(Category, payload.category_id):
        raise HTTPException(status_code=400, detail="分类不存在")
    data = payload.model_dump(exclude={"specs"})
    product = Product(**data)
    for spec in payload.specs:
        product.specs.append(ProductSpec(name=spec.name, price=spec.price, stock=spec.stock, sort=spec.sort))
    db.add(product)
    db.commit()
    db.refresh(product)
    return Resp(data={"id": product.id})


@router.put("/products/{product_id}", response_model=Resp)
def update_product(
    product_id: int,
    payload: AdminProductSpecIn,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if not db.get(Category, payload.category_id):
        raise HTTPException(status_code=400, detail="分类不存在")

    for key, value in payload.model_dump(exclude={"specs"}).items():
        setattr(product, key, value)

    incoming = {s.id for s in payload.specs if s.id}
    for spec in list(product.specs):
        if spec.id not in incoming:
            product.specs.remove(spec)
    for spec_in in payload.specs:
        if spec_in.id:
            existing = next((s for s in product.specs if s.id == spec_in.id), None)
            if existing:
                existing.name, existing.price, existing.stock, existing.sort = (
                    spec_in.name, spec_in.price, spec_in.stock, spec_in.sort
                )
        else:
            product.specs.append(
                ProductSpec(name=spec_in.name, price=spec_in.price, stock=spec_in.stock, sort=spec_in.sort)
            )
    db.commit()
    return Resp()


@router.put("/products/{product_id}/status", response_model=Resp)
def toggle_product_status(
    product_id: int, status: bool, db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)
):
    """商品上下架。"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.status = status
    db.commit()
    return Resp(data={"id": product.id, "status": product.status})


@router.put("/products/{product_id}/stock", response_model=Resp)
def update_stock(
    product_id: int,
    payload: StockUpdateIn,
    spec_id: str | None = None,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    """库存维护：传 spec_id 改对应规格库存，不传则改商品库存。"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if spec_id:
        spec = db.get(ProductSpec, int(spec_id))
        if not spec or spec.product_id != product.id:
            raise HTTPException(status_code=404, detail="规格不存在")
        spec.stock = payload.stock
    else:
        product.stock = payload.stock
    db.commit()
    return Resp()


@router.delete("/products/{product_id}", response_model=Resp)
def delete_product(product_id: int, db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    db.delete(product)
    db.commit()
    return Resp()


# ---------- 订单管理 ----------
@router.get("/orders", response_model=Resp)
def admin_orders(
    status: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    query = db.query(Order).options(selectinload(Order.items))
    if status is not None:
        query = query.filter(Order.status == status)
    if date_from:
        query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Order.created_at < datetime.fromisoformat(date_to) + timedelta(days=1))
    orders = query.order_by(Order.id.desc()).limit(500).all()
    data = []
    for order in orders:
        item = order_to_dict(order)
        data.append(item)
    return Resp(data=data)


@router.put("/orders/{order_no}/status", response_model=Resp)
def update_order_status(
    order_no: str, payload: OrderStatusIn, db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)
):
    """订单状态管理：核销完成 / 取消等。"""
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    order.status = payload.status
    db.commit()
    return Resp(data={"order_no": order.order_no, "status": order.status,
                      "status_text": ORDER_STATUS_TEXT.get(order.status, "")})


# ---------- 统计 ----------
@router.get("/stats", response_model=Resp)
def stats(db: Session = Depends(get_db), _: Admin = Depends(get_current_admin)):
    """订单数据简单统计：今日营收、订单数、待处理、热销商品。"""
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())

    paid_today = (
        db.query(func.count(Order.id), func.coalesce(func.sum(Order.pay_amount), 0))
        .filter(
            Order.created_at >= today_start,
            Order.status.in_([ORDER_STATUS_PAID, ORDER_STATUS_FINISHED]),
        )
        .first()
    )
    status_rows = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    status_map = {ORDER_STATUS_TEXT.get(s, str(s)): c for s, c in status_rows}

    hot = (
        db.query(OrderItem.product_name, func.sum(OrderItem.quantity).label("qty"))
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    total_revenue = (
        db.query(func.coalesce(func.sum(Order.pay_amount), 0))
        .filter(Order.status.in_([ORDER_STATUS_PAID, ORDER_STATUS_FINISHED]))
        .scalar()
    )

    return Resp(
        data={
            "today_order_count": paid_today[0] or 0,
            "today_revenue": round(float(paid_today[1] or 0), 2),
            "total_revenue": round(float(total_revenue or 0), 2),
            "status_count": status_map,
            "hot_products": [{"name": name, "quantity": int(qty)} for name, qty in hot],
        }
    )
