"""全局配置：从 .env / 环境变量读取。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "门店扫码点单系统"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./store_ordering.db"

    # JWT
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7
    ADMIN_JWT_EXPIRE_MINUTES: int = 60 * 12

    # 默认管理员
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    # 微信
    WECHAT_APPID: str = ""
    WECHAT_SECRET: str = ""
    WECHAT_MOCK: bool = True

    # 支付宝
    ALIPAY_APPID: str = ""
    ALIPAY_PRIVATE_KEY: str = ""
    ALIPAY_PUBLIC_KEY: str = ""
    ALIPAY_MOCK: bool = True

    # 支付
    PAY_MODE: str = "mock"  # mock | real
    WXPAY_MCHID: str = ""
    WXPAY_SERIAL_NO: str = ""
    WXPAY_API_V3_KEY: str = ""
    WXPAY_PRIVATE_KEY_PATH: str = ""
    WXPAY_NOTIFY_URL: str = ""
    ALIPAY_NOTIFY_URL: str = ""

    # 业务
    NEED_TABLE_NO: bool = False

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
