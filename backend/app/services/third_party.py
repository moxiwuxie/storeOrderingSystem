"""第三方能力封装：微信登录、支付宝登录、支付下单。

生产环境请把 mock 开关置为 false，并填入真实商户凭证。
"""
import hashlib
import time
import uuid

import requests

from ..config import settings


# ==================== 微信 ====================
def wechat_code2session(code: str) -> dict:
    """用 wx.login 的 code 换取 openid / session_key。"""
    if settings.WECHAT_MOCK or not settings.WECHAT_APPID:
        # 开发模式：由 code 派生稳定的模拟 openid，便于本地反复登录同一账号
        fake = hashlib.md5(f"mock-{code}".encode()).hexdigest()[:24]
        return {"openid": f"mock_openid_{fake}", "session_key": "mock_session_key"}

    resp = requests.get(
        "https://api.weixin.qq.com/sns/jscode2session",
        params={
            "appid": settings.WECHAT_APPID,
            "secret": settings.WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    data = resp.json()
    if "openid" not in data:
        raise ValueError(f"微信登录失败: {data}")
    return data


# ==================== 支付宝 ====================
def alipay_auth2user(auth_code: str) -> dict:
    """用支付宝 auth_code 换取 user_id（扫码/授权登录）。"""
    if settings.ALIPAY_MOCK or not settings.ALIPAY_APPID:
        fake = hashlib.md5(f"mock-ali-{auth_code}".encode()).hexdigest()[:24]
        return {"user_id": f"mock_alipay_{fake}"}

    # 真实环境：调用 alipay.system.oauth.token（此处仅保留骨架，需签名）
    raise NotImplementedError(
        "支付宝真实登录需配置应用私钥并调用 alipay.system.oauth.token 完成验签，"
        "请参考官方文档补齐 alipay_auth2user 实现。"
    )


# ==================== 支付 ====================
def create_wechat_pay(order_no: str, amount: float, openid: str, description: str) -> dict:
    """微信小程序内支付（JSAPI）。mock 模式返回模拟参数。"""
    if settings.PAY_MODE == "mock":
        return {
            "timeStamp": str(int(time.time())),
            "nonceStr": uuid.uuid4().hex,
            "package": f"prepay_id=mock_{order_no}",
            "signType": "RSA",
            "paySign": "mock_sign",
        }

    # 真实环境需使用微信支付 v3 SDK 完成签名与请求
    raise NotImplementedError(
        "微信 JSAPI 支付需配置商户号、证书序列号、APIv3 密钥与商户私钥，"
        "并调用 https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi 完成签名下单。"
    )


def create_wechat_h5_pay(order_no: str, amount: float, description: str, client_ip: str = "") -> dict:
    """微信 H5 支付（浏览器内）。返回 mweb_url 供前端跳转。"""
    if settings.PAY_MODE == "mock":
        return {"h5_url": f"https://mock.wechatpay/h5/{order_no}", "package": f"prepay_id=mock_{order_no}"}

    raise NotImplementedError(
        "微信 H5 支付需在 https://api.mch.weixin.qq.com/v3/pay/transactions/h5 下单，"
        "并携带场景信息 scene_info（h5_info.type=Wap、wap_url、wap_name），返回 mweb_url 供前端跳转。"
    )


def create_alipay_pay(order_no: str, amount: float, subject: str) -> str:
    """支付宝小程序内支付，返回用于拉起收银台的 orderStr。mock 模式返回模拟串。"""
    if settings.PAY_MODE == "mock":
        return f"alipay_mock_order_str_{order_no}"

    raise NotImplementedError(
        "支付宝小程序支付需配置应用私钥，并调用 alipay.trade.create 完成签名。"
    )


def create_alipay_h5_pay(order_no: str, amount: float, subject: str, return_url: str = "") -> str:
    """支付宝手机网站支付（浏览器内），返回可直接跳转的表单 HTML。"""
    if settings.PAY_MODE == "mock":
        return f"<form id='mock' action='https://mock.alipay/h5/{order_no}'></form>"

    raise NotImplementedError(
        "支付宝手机网站支付需配置应用私钥，调用 alipay.trade.wap.pay 并签名，"
        "返回自动提交的 <form> 表单 HTML 供浏览器跳转收银台。"
    )


def verify_wechat_notify(headers: dict, body: bytes) -> dict:
    """校验并解密微信支付回调。生产环境需验签 + AES-GCM 解密。"""
    if settings.PAY_MODE == "mock":
        return {"trade_state": "SUCCESS"}
    raise NotImplementedError("微信支付回调验签与解密需接入微信支付 v3 平台证书，请参考官方文档实现。")


def verify_alipay_notify(form: dict) -> bool:
    """校验支付宝回调签名。生产环境需用支付宝公钥验签。"""
    if settings.PAY_MODE == "mock":
        return True
    raise NotImplementedError("支付宝回调验签需使用支付宝公钥，请参考官方文档实现。")
