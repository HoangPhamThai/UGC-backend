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

    creator_email: Optional[str] = Field(default=None, alias="CREATOR_EMAIL")
    creator_password: Optional[str] = Field(default=None, alias="CREATOR_PASSWORD")

    qc_email: Optional[str] = Field(default=None, alias="QC_EMAIL")
    qc_password: Optional[str] = Field(default=None, alias="QC_PASSWORD")
    # Comma-separated list of product codes the default QC covers, e.g. "CL,MMF".
    qc_products: Optional[str] = Field(default=None, alias="QC_PRODUCTS")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment


settings = Settings()
