"""应用入口：注册路由、静态资源、初始化数据。"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from .config import settings
from .database import Base, SessionLocal, engine
from .models import Admin, Category, Product, ProductSpec
from .routers import admin, auth, cart, orders, payment, products
from .security import hash_password

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


def seed_data() -> None:
    """首次启动写入默认管理员与演示商品。"""
    db = SessionLocal()
    try:
        if not db.query(Admin).first():
            db.add(
                Admin(
                    username=settings.ADMIN_USERNAME,
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    real_name="店长",
                )
            )

        if not db.query(Category).first():
            drinks = Category(name="招牌饮品", sort=1)
            snacks = Category(name="小吃甜点", sort=2)
            db.add_all([drinks, snacks])
            db.flush()

            p1 = Product(
                category_id=drinks.id, name="招牌珍珠奶茶", description="手作珍珠，茶香浓郁",
                price=18.0, stock=0, unit="杯", sort=1,
            )
            p1.specs = [
                ProductSpec(name="中杯 常温", price=16.0, stock=50, sort=1),
                ProductSpec(name="大杯 常温", price=18.0, stock=50, sort=2),
                ProductSpec(name="大杯 少冰", price=19.0, stock=30, sort=3),
            ]
            p2 = Product(
                category_id=drinks.id, name="美式咖啡", description="精选阿拉比卡豆，回甘持久",
                price=15.0, stock=80, unit="杯", sort=2,
            )
            p3 = Product(
                category_id=snacks.id, name="香酥鸡米花", description="现炸酥脆，佐以椒盐",
                price=12.0, stock=40, unit="份", sort=1,
            )
            p4 = Product(
                category_id=snacks.id, name="提拉米苏", description="经典意式甜点",
                price=22.0, stock=0, unit="份", sort=2,
            )
            p4.specs = [
                ProductSpec(name="原味", price=22.0, stock=15, sort=1),
                ProductSpec(name="抹茶味", price=24.0, stock=10, sort=2),
            ]
            db.add_all([p1, p2, p3, p4])
        db.commit()
    finally:
        db.close()


def ensure_columns() -> None:
    """轻量迁移：为已存在的库补齐后续新增的列（SQLite / MySQL 通用）。"""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("users")}
    if "device_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN device_id VARCHAR(64)"))
            conn.execute(text("CREATE UNIQUE INDEX ix_users_device_id ON users (device_id)"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_columns()
    seed_data()
    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一错误结构：{code:1, msg, data:null}，便于小程序端统一处理。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": 1, "msg": exc.detail, "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query", "path"))
    msg = f"参数校验失败：{field} {first.get('msg', '')}".strip()
    return JSONResponse(status_code=422, content={"code": 1, "msg": msg, "data": None})


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(payment.router)
app.include_router(admin.router)


@app.get("/api/health", tags=["系统"])
def health():
    return {"code": 0, "msg": "ok", "data": {"app": settings.APP_NAME, "pay_mode": settings.PAY_MODE}}


# 静态前端：商家后台 /admin/ ，H5 点单页 /h5/
if STATIC_DIR.exists():
    admin_dir = STATIC_DIR / "admin"
    if admin_dir.exists():
        app.mount("/admin", StaticFiles(directory=str(admin_dir), html=True), name="admin")
    h5_dir = STATIC_DIR / "h5"
    if h5_dir.exists():
        app.mount("/h5", StaticFiles(directory=str(h5_dir), html=True), name="h5")


@app.get("/", include_in_schema=False)
def index():
    """访问根路径时给出各端入口导航。"""
    return {
        "code": 0,
        "msg": "ok",
        "data": {
            "h5": "/h5/",
            "admin": "/admin/",
            "docs": "/docs",
        },
    }
