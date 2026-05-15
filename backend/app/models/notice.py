from sqlalchemy import (
    Index,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    ARRAY,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum, uuid

from app.database import Base


class NoticeType(str, enum.Enum):
    INFORMATIVE = "informativo"
    URGENT = "urgente"
    CRITICAL = "crítico"


class NoticeStatus(str, enum.Enum):
    ACTIVE = "activo"
    DRAFT = "borrador"
    ARCHIVED = "archivado"


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[NoticeType] = mapped_column(
        SAEnum(NoticeType), nullable=False, index=True
    )
    status: Mapped[NoticeStatus] = mapped_column(
        SAEnum(NoticeStatus),
        nullable=False,
        default=NoticeStatus.DRAFT,
        index=True,
    )
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    media_keys: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )


class NotificationChannel(str, enum.Enum):
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, enum.Enum):
    PENDING = "pendiente"
    SENT = "enviado"
    DELIVERED = "entregado"
    FAILED = "fallido"


class NotificactionLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    notice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel), nullable=False
    )
    status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.utcnow(), nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        Index("ix_notif_log_notice_channel_status", "notice_id", "channel", "status"),
    )
