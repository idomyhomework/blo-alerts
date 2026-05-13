from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User, UserRole
from app.core.security import decode_token

# tokenUrl es solo para que Swagger muestre el botón de login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependencia: extrae el usuario del JWT.
    Lanza 401 si el token no es válido o no existe.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado.",
        )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token incorrecto.",
            )
        user_id = payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
        )

    user = await db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido.",
        )
    return user


def require_role(*roles: UserRole):
    """
    Factory de dependencia: devuelve un Depends que valida el rol.
    Uso: user: User = Depends(require_role(UserRole.GUARD))
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta acción.",
            )
        return user

    return _check


# Atajos para usar directamente en los routers
require_guard = require_role(UserRole.GUARD, UserRole.SUPERADMIN)
require_superadmin = require_role(UserRole.SUPERADMIN)
require_citizen = require_role(UserRole.CITIZEN)
