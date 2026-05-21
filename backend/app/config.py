from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/app.db"
    odbc_connection_string: Optional[str] = "DSN=HAC_HO;"
    whatsapp_service_url: str = "http://localhost:3001"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 480

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
