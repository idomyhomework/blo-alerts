import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_session
from app.models.user import User, UserRole
from app.models.otp import OTPCode
from app.schemas.auth import (
    RequestOTPIn,
    RequestOTPOut,
    VerifyOTPIn,
    LoginIn,
    RefreshIn,
    TokenPair,
)
from app.core.security import (
    generate_otp_code,
    hash_otp,
    verify_otp as check_otp_hash,
    verify_secret,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.sms import get_sms_service
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# ----------------------------------------------------------------
# POST /auth/request-otp
# ----------------------------------------------------------------
@router.post("/request-otp", response_model=RequestOTPOut)
async def request_otp(
    payload: RequestOTPIn,
    db: AsyncSession = Depends(get_session),
):
    """
    Genera un OTP, lo guarda hasheado y lo envía por SMS.
    Mensaje genérico: no revelamos si el número está registrado o no.
    """
    # 1. Comprobar intentos recientes para este teléfono
    window_start = datetime.now(timezone.utc) - timedelta(
        minutes=settings.OTP_WINDOW_MINUTES
    )
    stmt = (
        select(func.count())
        .select_from(OTPCode)
        .where(
            OTPCode.phone == payload.phone,
            OTPCode.created_at >= window_start,
        )
    )
    recent_count = (await db.execute(stmt)).scalar()
    if recent_count >= settings.OTP_MAX_ATTEMPTS_PER_PHONE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos.",
        )

    # 2. Generar OTP criptográficamente seguro
    code = generate_otp_code(6)

    # 3. Guardar HASHEADO. Nunca en claro.
    otp = OTPCode(
        phone=payload.phone,
        code_hash=hash_otp(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(otp)
    await db.commit()

    # 4. Enviar SMS
    # En desarrollo con placeholder de Twilio, logueamos el código
    if settings.ENV == "development":
        logger.warning("⚠ [DEV] OTP para %s → %s", payload.phone, code)

    sent = get_sms_service().send_otp(payload.phone, code)
    if not sent and settings.ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo enviar el SMS. Intenta más tarde.",
        )

    return RequestOTPOut()


# ----------------------------------------------------------------
# POST /auth/verify-otp
# ----------------------------------------------------------------
@router.post("/verify-otp", response_model=TokenPair)
async def verify_otp(
    payload: VerifyOTPIn,
    db: AsyncSession = Depends(get_session),
):
    """Verifica el OTP. Si es correcto, crea/actualiza el usuario y devuelve tokens."""
    now = datetime.now(timezone.utc)

    # 1. Buscar OTP válido para este teléfono
    stmt = (
        select(OTPCode)
        .where(
            OTPCode.phone == payload.phone,
            OTPCode.used_at.is_(None),
            OTPCode.expires_at > now,
            OTPCode.attempts < 5,
        )
        .order_by(OTPCode.created_at.desc())
        .limit(1)
    )
    otp = (await db.execute(stmt)).scalar_one_or_none()
    if otp is None:
        raise HTTPException(400, "Código inválido o expirado.")

    # 2. Verificar el código contra el hash
    if not check_otp_hash(payload.code, otp.code_hash):
        otp.attempts += 1
        await db.commit()
        raise HTTPException(400, "Código inválido o expirado.")

    # 3. Marcar OTP como usado
    otp.used_at = now

    # 4. Crear o recuperar el usuario
    user_stmt = select(User).where(
        User.phone == payload.phone, User.deleted_at.is_(None)
    )
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if user is None:
        user = User(phone=payload.phone, role=UserRole.CITIZEN, verified_at=now)
        db.add(user)
        await db.flush()
    else:
        user.verified_at = now

    # 5. Guardar token FCM si vino
    if payload.fcm_token:
        user.fcm_token = payload.fcm_token

    await db.commit()

    # 6. Generar tokens según rol
    access = create_access_token(str(user.id), user.role.value)
    refresh, _ = create_refresh_token(
        str(user.id), days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS_CITIZEN
    )

    return TokenPair(access_token=access, refresh_token=refresh)


# ----------------------------------------------------------------
# POST /auth/login (guardias y superadmins)
# ----------------------------------------------------------------
@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginIn,
    db: AsyncSession = Depends(get_session),
):
    """Login para guards y superadmins con email y contraseña."""
    stmt = select(User).where(User.email == payload.email, User.deleted_at.is_(None))
    user = (await db.execute(stmt)).scalar_one_or_none()

    # Verificar contraseña siempre, aunque el usuario no exista.
    # Evita timing attacks: si saltamos el verify cuando user=None,
    # la respuesta es más rápida y un atacante deduce qué emails existen.
    dummy_hash = "$2b$12$KIXiCqBKIFKQXL6X6X6X6OqKQXL6X6X6X6X6X6X6X6X6X6X6X6X6"
    pwd_ok = verify_secret(payload.password, user.password_hash if user else dummy_hash)

    if not user or not pwd_ok or user.role not in (UserRole.GUARD, UserRole.SUPERADMIN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
        )

    access = create_access_token(str(user.id), user.role.value)

    # Días de expiración según rol
    days = (
        settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS_GUARD
        if user.role == UserRole.GUARD
        else settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS_SUPERADMIN
    )
    refresh, _ = create_refresh_token(str(user.id), days=days)

    return TokenPair(access_token=access, refresh_token=refresh)


# ----------------------------------------------------------------
# POST /auth/refresh
# ----------------------------------------------------------------
@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshIn,
    db: AsyncSession = Depends(get_session),
):
    """Genera un nuevo access token usando el refresh token."""
    from jose import JWTError

    try:
        data = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(401, "Refresh token inválido.")

    if data.get("type") != "refresh":
        raise HTTPException(401, "Token incorrecto.")

    user = await db.get(User, data["sub"])
    if user is None or user.deleted_at is not None:
        raise HTTPException(401, "Usuario no válido.")

    access = create_access_token(str(user.id), user.role.value)
    return TokenPair(access_token=access, refresh_token=payload.refresh_token)


# ----------------------------------------------------------------
# POST /auth/logout
# ----------------------------------------------------------------
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshIn):
    """
    Invalida el refresh token.
    Por ahora devuelve 204 — en la Fase 2 añadiremos Redis para revocación real.
    """
    pass
