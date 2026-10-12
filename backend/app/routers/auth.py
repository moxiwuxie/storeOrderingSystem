"""登录模块：微信授权登录、支付宝扫码登录、当前用户信息。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import AlipayLoginIn, H5LoginIn, LoginOut, Resp, WechatLoginIn
from ..security import create_token
from ..services.third_party import alipay_auth2user, wechat_code2session

router = APIRouter(prefix="/api/auth", tags=["登录"])


def _login_by_identity(db: Session, field: str, value: str, nickname: str, avatar: str) -> LoginOut:
    user = db.query(User).filter(getattr(User, field) == value).first()
    if not user:
        user = User(nickname=nickname or "微信用户", avatar=avatar or "")
        setattr(user, field, value)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        changed = False
        if nickname and user.nickname != nickname:
            user.nickname, changed = nickname, True
        if avatar and user.avatar != avatar:
            user.avatar, changed = avatar, True
        if changed:
            db.commit()
    return LoginOut(token=create_token(user.id, "user"), user_id=user.id, nickname=user.nickname, avatar=user.avatar)


@router.post("/wechat", response_model=Resp)
def wechat_login(payload: WechatLoginIn, db: Session = Depends(get_db)):
    """微信小程序授权登录：前端 wx.login 拿 code，后端换 openid。"""
    try:
        session = wechat_code2session(payload.code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = _login_by_identity(db, "openid", session["openid"], payload.nickname, payload.avatar)
    return Resp(data=result.model_dump())


@router.post("/alipay", response_model=Resp)
def alipay_login(payload: AlipayLoginIn, db: Session = Depends(get_db)):
    """支付宝扫码授权登录：前端拿 auth_code，后端换 user_id。"""
    try:
        info = alipay_auth2user(payload.auth_code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = _login_by_identity(db, "alipay_user_id", info["user_id"], payload.nickname, payload.avatar)
    return Resp(data=result.model_dump())


@router.post("/h5", response_model=Resp)
def h5_login(payload: H5LoginIn, db: Session = Depends(get_db)):
    """H5（浏览器 / 支付宝内打开）登录。

    免注册识别顺序：支付宝授权码 > 手机号 > 设备标识。
    首次访问自动建号，无需短信验证等复杂注册流程。
    """
    alipay_user_id = None
    if payload.auth_code:
        try:
            alipay_user_id = alipay_auth2user(payload.auth_code)["user_id"]
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = None
    if alipay_user_id:
        user = db.query(User).filter(User.alipay_user_id == alipay_user_id).first()
    if not user and payload.phone:
        user = db.query(User).filter(User.phone == payload.phone).first()
    if not user:
        user = db.query(User).filter(User.device_id == payload.device_id).first()

    if not user:
        user = User(nickname=payload.nickname or "顾客", device_id=payload.device_id)
        db.add(user)

    if alipay_user_id:
        user.alipay_user_id = alipay_user_id
    if payload.phone:
        user.phone = payload.phone
    if payload.nickname:
        user.nickname = payload.nickname
    if payload.avatar:
        user.avatar = payload.avatar
    # 设备标识仅在未占用时补齐，避免与其它账号冲突
    if not user.device_id:
        user.device_id = payload.device_id

    db.commit()
    db.refresh(user)
    return Resp(
        data=LoginOut(
            token=create_token(user.id, "user"), user_id=user.id,
            nickname=user.nickname, avatar=user.avatar,
        ).model_dump()
    )


@router.get("/profile", response_model=Resp)
def profile(user: User = Depends(get_current_user)):
    return Resp(
        data={
            "user_id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "phone": user.phone,
            "bind_wechat": bool(user.openid),
            "bind_alipay": bool(user.alipay_user_id),
        }
    )
