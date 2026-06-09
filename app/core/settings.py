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

    redis_url: str = Field(default="redis://redis:6380/0", alias="REDIS_URL")
    register_rate_limit: str = Field(default="5/hour;20/day", alias="REGISTER_RATE_LIMIT")
    trust_forwarded_for: bool = Field(default=True, alias="TRUST_FORWARDED_FOR")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment


settings = Settings()
