# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # E-mail (Resend)
    RESEND_API_KEY: str
    ADMIN_EMAILS: str
    EMAIL_FROM: str = "onboarding@resend.dev"
    
    # Emissão NFSe
    NFSE_ACCESS_KEY: str
    NFSE_CN: str
    NFSE_URL: str  # ex: https://provedor.gov.br/Service.asmx

    class Config:
        env_file = ".env"


settings = Settings()
