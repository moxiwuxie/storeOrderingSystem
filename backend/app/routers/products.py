"""商品展示模块：分类 + 商品列表 + 商品详情（无需登录）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Category, Product
from ..schemas import Resp

router = APIRouter(prefix="/api/products", tags=["商品"])


@router.get("/categories", response_model=Resp)
def list_categories(db: Session = Depends(get_db)):
    """分类（含在售商品），供点单页左侧分类 + 右侧商品联动展示。"""
    categories = (
        db.query(Category)
        .filter(Category.status.is_(True))
        .options(selectinload(Category.products).selectinload(Product.specs))
        .order_by(Category.sort.asc(), Category.id.asc())
        .all()
    )
    data = []
    for category in categories:
        products = [p for p in category.products if p.status]
        products.sort(key=lambda p: (p.sort, p.id))
        data.append(
            {
                "id": category.id,
                "name": category.name,
                "sort": category.sort,
                "products": [_product_dict(p) for p in products],
            }
        )
    return Resp(data=data)


@router.get("", response_model=Resp)
def list_products(category_id: int | None = None, keyword: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Product).filter(Product.status.is_(True)).options(selectinload(Product.specs))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if keyword:
        query = query.filter(Product.name.like(f"%{keyword}%"))
    products = query.order_by(Product.sort.asc(), Product.id.asc()).all()
    return Resp(data=[_product_dict(p) for p in products])


@router.get("/{product_id}", response_model=Resp)
def product_detail(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or not product.status:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")
    return Resp(data=_product_dict(product))


def _product_dict(product: Product) -> dict:
    """统一商品输出结构：有规格时展示最低价与规格库存合计。"""
    specs = sorted(product.specs, key=lambda s: (s.sort, s.id))
    if specs:
        price = min(float(s.price) for s in specs)
        stock = sum(s.stock for s in specs)
    else:
        price = float(product.price)
        stock = product.stock
    return {
        "id": product.id,
        "category_id": product.category_id,
        "name": product.name,
        "description": product.description,
        "image": product.image,
        "price": price,
        "stock": stock,
        "unit": product.unit,
        "status": product.status,
        "specs": [
            {"id": s.id, "name": s.name, "price": float(s.price), "stock": s.stock} for s in specs
        ],
    }
