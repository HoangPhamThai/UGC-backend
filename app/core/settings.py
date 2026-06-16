from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    db_host: str = Field(default="", alias="DB_HOST")
    db_name: str = Field(default="", alias="DB_NAME")
    db_timeout: int = Field(default=5000, alias="DB_TIMEOUT")

    jwt_secret_key: str = Field(default="", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=2, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # --- Default bootstrap accounts ---
    superuser_email: Optional[str] = Field(default=None, alias="SUPERUSER_EMAIL")
    superuser_password: Optional[str] = Field(default=None, alias="SUPERUSER_PASSWORD")

    admin_email: Optional[str] = Field(default=None, alias="ADMIN_EMAIL")
    admin_password: Optional[str] = Field(default=None, alias="ADMIN_PASSWORD")

    # Comma-separated lists; emails[i] is paired with passwords[i].
    creator_emails: Optional[str] = Field(default=None, alias="CREATOR_EMAILS")
    creator_passwords: Optional[str] = Field(default=None, alias="CREATOR_PASSWORDS")

    qc_email: Optional[str] = Field(default=None, alias="QC_EMAIL")
    qc_password: Optional[str] = Field(default=None, alias="QC_PASSWORD")
    # Comma-separated list of product codes the default QC covers, e.g. "CL,MMF".
    qc_products: Optional[str] = Field(default=None, alias="QC_PRODUCTS")

    # --- MinIO object storage (acceptance reports) ---
    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="acceptance-reports", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # --- Email (QC creator notifications via Gmail SMTP) ---
    from_email: Optional[str] = Field(default=None, alias="FROM_EMAIL")
    email_app_password: Optional[str] = Field(default=None, alias="EMAIL_APP_PASSWORD")
    frontend_base_url: Optional[str] = Field(default=None, alias="FRONTEND_BASE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment


settings = Settings()
