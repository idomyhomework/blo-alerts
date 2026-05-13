import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(str, enum.Enum):
    CITIZEN = "ciudadano"  # Ciudadano normal con app
    POLICE = "policia"  # Guardia: puede crear avisos
    SUPERADMIN = "superadmin"  # Admin del sistema


class User(Base):
    __tablename__ = "users"

    # UUID como primary key: no expone cuántos usuarios hay
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Teléfono en formato E.164 (+34612345678)
    # nullable porque los superadmins pueden no tenerlo
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)

    # Email solo para guards y superadmins
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)

    # Hash bcrypt de la contraseña. NUNCA en claro.
    password_hash: Mapped[str | None] = mapped_column(String(255))

    # Fecha en la que verificó su teléfono. NULL = no verificado.
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Token FCM para enviar push. Se actualiza cada vez que la app arranca.
    fcm_token: Mapped[str | None] = mapped_column(String(512))

    # Rol del usuario
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        default=UserRole.CITIZEN,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Soft delete: si está poblado, el usuario está "borrado"
    # pero no físicamente — necesitamos auditoría histórica
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
