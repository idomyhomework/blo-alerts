from decouple import config, Csv
from pydantic import BaseModel
from functools import lru_cache


class Settings(BaseModel):
    # -- General --
    ENV: str = config("ENV", default="development")
    LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
    # --- Base de datos ---
    DATABASE_URL: str = config("DATABASE_URL")
    # --- API ---
    CORS_ORIGINS: list = config(
        "CORS_ORIGINS", cast=Csv(), default="http://localhost:5173"
    )
    # --- JWT (tokens de acceso) ---
    JWT_SECRET_KEY: str = config("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = config(
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", cast=int, default=15
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS_CITIZEN: int = config(
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS_CITIZEN", cast=int, default=90
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS_GUARD: int = config(
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS_GUARD", cast=int, default=30
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS_SUPERADMIN: int = config(
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS_SUPERADMIN", cast=int, default=15
    )
    # --- OTP / Rate limiting ---
    OTP_MAX_ATTEMPTS_PER_PHONE: int = config(
        "OTP_MAX_ATTEMPTS_PER_PHONE", cast=int, default=3
    )
    OTP_WINDOW_MINUTES: int = config("OTP_WINDOW_MINUTES", cast=int, default=10)
    # --- Twilio ---
    TWILIO_ACCOUNT_SID: str = config("TWILIO_ACCOUNT_SID", default="")
    TWILIO_AUTH_TOKEN: str = config("TWILIO_AUTH_TOKEN", default="")
    TWILIO_FROM_NUMBER: str = config("TWILIO_FROM_NUMBER", default="")
    TWILIO_OTP_TEMPLATE: str = config(
        "TWILIO_OTP_TEMPLATE",
        default="Tu código de verificación es: {code}. Caduca en 5 min.",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
