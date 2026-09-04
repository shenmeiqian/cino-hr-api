"""Application settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "demo-key"
    database_url: str = "sqlite:///./cino_hr.db"
    app_title: str = "CINO HR API"
    app_version: str = "0.2.0"

    # Phase2: merge PositionRole into effective roles on login/me (default true for demo)
    sync_roles_from_position: bool = True

    # File storage: local | s3 | database
    file_storage_backend: str = "local"
    file_local_dir: str = "/workspace/cino-hr-api/data/files"
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # OIDC SSO
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/sso/callback"
    oidc_frontend_redirect: str = "http://127.0.0.1:5173/login"

    # Notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@cino.demo"
    wecom_webhook_url: str = ""
    dingtalk_webhook_url: str = ""
    feishu_webhook_url: str = ""
    sms_provider: str = "demo"  # demo|aliyun|tencent
    aliyun_sms_access_key: str = ""
    aliyun_sms_secret: str = ""
    tencent_sms_secret_id: str = ""
    tencent_sms_secret_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
