import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing (bcrypt) ──────────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
)


def hash_secret(secret: str) -> str:
    """Hashea contraseñas con bcrypt. Solo para passwords, no para OTPs."""
    return pwd_context.hash(secret[:72])


def verify_secret(plain: str, hashed: str) -> bool:
    """
    Verifica una contraseña contra su hash bcrypt.
    Constant-time para evitar timing attacks.
    """
    return pwd_context.verify(plain[:72], hashed)


# ── OTP hashing (HMAC-SHA256) ──────────────────────────────────────────────
def hash_otp(code: str) -> str:
    """
    Hashea un OTP con SHA-256.
    Los OTPs tienen TTL corto y rate limiting — no necesitan key-stretching.
    """
    return hashlib.sha256(code.encode()).hexdigest()


def verify_otp(code: str, hashed: str) -> bool:
    """Verifica un OTP en tiempo constante para evitar timing attacks."""
    return hmac.compare_digest(hashlib.sha256(code.encode()).hexdigest(), hashed)


def generate_otp_code(length: int = 6) -> str:
    """
    Genera un OTP numérico criptográficamente seguro.
    Usa secrets.choice (generador del SO), no random (que es predecible).
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


def create_access_token(user_id: str, role: str) -> str:
    """Crea un JWT de acceso firmado con el secret del entorno."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,  # subject: a quién pertenece el token
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token(user_id: str, days: int) -> tuple[str, datetime]:
    """
    Crea un refresh token.
    days se pasa desde el router según el rol:
    - settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS_CITIZEN
    - settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS_GUARD
    - settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS_SUPERADMIN
    """
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token, expire


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un JWT.
    Lanza JWTError si es inválido o expiró.
    """
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
