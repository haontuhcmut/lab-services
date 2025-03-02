from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

current_path = Path(__file__).resolve()
env_path = current_path.parent.parent / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    REDIS_URL: str = "redis://localhost:6379/0"
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    DOMAIN: str
    ACCESS_TOKEN_EXPIRES_MINUTES: int
    ACCESS_TOKEN_EXPIRES_DEFAULT: int
    REFRESH_TOKEN_EXPIRES_DAYS_DEFAULT: int
    MODEL_PATH: str
    # ADMIN CONFIG
    FIRST_NAME: str
    LAST_NAME: str
    ADMIN_NAME: str
    EMAIL: str
    PASSWORD: str

    model_config = SettingsConfigDict(env_file=env_path, extra="ignore")


Config = Settings()

broker_url = Config.REDIS_URL
result_backend = Config.REDIS_URL
broker_connection_retry_on_startup = True
