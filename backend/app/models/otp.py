from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
import uuid
from app.database import Base


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # El número de teléfono al que se envió. Indexado: muchas búsquedas por phone.
    phone: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    # IMPORTANTE: el OTP se guarda HASHEADO con bcrypt, no en claro.
    # Si alguien volcara la BD, no podría leer los códigos.
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Cuándo expira (now + 5 min en el momento de crear).
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # Fecha en la que se usó. Si está poblado, ya no se puede reutilizar.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Intentos fallidos al verificar este código. A los 5, se invalida.
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
