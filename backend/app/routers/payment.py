"""支付模块：发起支付 + 支付回调（支付成功后回写订单状态）。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import ORDER_STATUS_PAID, ORDER_STATUS_PENDING, Order, User
from ..deps import get_current_user
from ..schemas import PayIn, Resp
from ..services.third_party import (
    create_alipay_h5_pay,
    create_alipay_pay,
    create_wechat_h5_pay,
    create_wechat_pay,
    verify_alipay_notify,
    verify_wechat_notify,
)

router = APIRouter(prefix="/api/payment", tags=["支付"])


@router.post("/prepay", response_model=Resp)
def prepay(payload: PayIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发起支付，按「渠道 + 来源端」返回对应的支付参数。

    来源端 source：
    - miniprogram：微信小程序 JSAPI / 支付宝小程序 orderStr
    - h5：浏览器或支付宝内打开的 H5（微信 H5 支付 mweb_url / 支付宝手机网站支付表单）

    PAY_MODE=mock 时会直接标记支付成功，方便本地与联调环境跑通全流程。
    """
    order = db.query(Order).filter(Order.order_no == payload.order_no, Order.user_id == user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != ORDER_STATUS_PENDING:
        raise HTTPException(status_code=400, detail="该订单当前状态不可支付")

    subject = f"订单{order.order_no}"
    amount = float(order.pay_amount)
    is_h5 = payload.source == "h5"

    if payload.pay_type == "wechat":
        if is_h5:
            pay_params = create_wechat_h5_pay(order.order_no, amount, subject)
            pay_params["mode"] = "h5_redirect"
        else:
            pay_params = create_wechat_pay(order.order_no, amount, user.openid or "", subject)
            pay_params["mode"] = "jsapi"
    else:
        if is_h5:
            pay_params = {"form_html": create_alipay_h5_pay(order.order_no, amount, subject), "mode": "h5_form"}
        else:
            pay_params = {"orderStr": create_alipay_pay(order.order_no, amount, subject), "mode": "order_str"}

    paid = False
    if settings.PAY_MODE == "mock":
        order.status = ORDER_STATUS_PAID
        order.pay_type = payload.pay_type
        order.pay_time = datetime.now()
        order.transaction_id = f"MOCK{order.order_no}"
        db.commit()
        paid = True

    return Resp(
        data={
            "order_no": order.order_no,
            "pay_type": payload.pay_type,
            "mock": settings.PAY_MODE == "mock",
            "pay_params": pay_params,
            "paid": paid,
        }
    )


@router.post("/wechat/notify")
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    """微信支付结果回调。"""
    body = await request.body()
    result = verify_wechat_notify(dict(request.headers), body)
    if result.get("trade_state") != "SUCCESS":
        return {"code": "FAIL", "message": "未支付成功"}

    out_trade_no = result.get("out_trade_no") or _extract_out_trade_no(body)
    if not out_trade_no:
        return {"code": "FAIL", "message": "缺少订单号"}

    _mark_paid(db, out_trade_no, "wechat", result.get("transaction_id", ""))
    return {"code": "SUCCESS", "message": "成功"}


@router.post("/alipay/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    """支付宝支付结果回调。"""
    form = dict(await request.form())
    if not verify_alipay_notify(form):
        return "failure"
    if form.get("trade_status") not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return "failure"

    _mark_paid(db, form.get("out_trade_no", ""), "alipay", form.get("trade_no", ""))
    return "success"


def _mark_paid(db: Session, order_no: str, pay_type: str, transaction_id: str) -> None:
    if not order_no:
        return
    order = db.query(Order).filter(Order.order_no == order_no).first()
    if not order or order.status != ORDER_STATUS_PENDING:
        return
    order.status = ORDER_STATUS_PAID
    order.pay_type = pay_type
    order.pay_time = datetime.now()
    order.transaction_id = transaction_id
    db.commit()


def _extract_out_trade_no(body: bytes) -> str:
    import json

    try:
        data = json.loads(body.decode() or "{}")
        return data.get("out_trade_no", "")
    except (ValueError, UnicodeDecodeError):
        return ""
