import logging

from backend.app.models import user
from backend.app.schemas import notice
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from uuid import UUID
from app.database import get_session
from app.models.notice import Notice, NoticeStatus, NoticeType
from app.models.user import User, UserRole
from app.schemas.notice import NoticeCreateIn, NoticeUpdateIn, NoticeOut
from app.core.auth import require_guard, get_current_user
from app.services.media import media_service
from app.workers.tasks import dispatch_push, schedule_sms_fallback
from app.config import settings

router = APIRouter(prefix="/notices", tags=["notices"])
audit_logger = logging.getLogger("audit")


def _to_out(notice: Notice) -> NoticeOut:
    """Convierte un Notice en NoticeOut firmando las URLs de medios."""
    out = NoticeOut.model_validate(notice)
    out.media_urls = [media_service.signed_url(k) for k in notice.media_keys]
    return out


@router.post("/", response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
async def create_notice(
    notice_in: NoticeCreateIn,
    current_user: User = Depends(require_guard),
    db: AsyncSession = Depends(get_session),
):
    """Crea un nuevo aviso. Solo para guardias."""
    new_notice = Notice(
        type=notice_in.type,
        description=notice_in.description,
        location_lat=notice_in.location_lat,
        location_lon=notice_in.location_lon,
        created_by=current_user.id,
        media_keys=[m.key for m in notice_in.media] if notice_in.media else [],
    )
    db.add(new_notice)
    await db.commit()
    await db.refresh(new_notice)

    # Auditoría: quién creó qué y cuándo. Veremos esto a fondo en seguridad.
    audit_logger.info(
        "notice.created",
        extra={
            "notice_id": str(new_notice.id),
            "by": str(current_user.id),
            "type": new_notice.type.value,
        },
    )

    return _to_out(new_notice)


@router.get("/", response_model=list[NoticeOut])
async def list_notices(
    status: NoticeStatus | None = None,
    type: NoticeType | None = None,
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    """Lista avisos. Los ciudadanos solo ven los suyos, los guardias ven todos."""
    query = (
        select(Notice)
        .order_by(Notice.created_at.desc())
        .limit(min(limit, 100))
        .offset(offset)
    )
    if current_user.role == UserRole.CITIZEN:
        query = query.where(Notice.status == NoticeStatus.ACTIVE)
    elif status:
        query = query.where(Notice.status == status)
    if type:
        query = query.where(Notice.type == type)
    notices = (await db.execute(query)).scalars().all()
    return [_to_out(n) for n in notices]


@router.get("/{notice_id}", response_model=NoticeOut)
async def get_notice(
    notice_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Obtiene un aviso por ID. Solo para guardias."""
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    if not notice:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    if current_user.role != UserRole.POLICE and notice.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    return _to_out(notice)


@router.put("/{notice_id}", response_model=NoticeOut)
async def update_notice(
    notice_id: UUID,
    notice_in: NoticeUpdateIn,
    current_user: User = Depends(require_guard),
    db: AsyncSession = Depends(get_session),
):
    """Actualiza un aviso. Solo para guardias."""
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = result.scalar_one_or_none()
    # Autorización: solo el autor o un superadmin. Defensa contra IDOR
    # (Insecure Direct Object Reference): un guardia no puede editar avisos
    # de otro guardia con solo cambiar el id en la URL.
    if not notice:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    if (
        notice.created_by != current_user.id
        and current_user.role != UserRole.SUPERADMIN
    ):
        raise HTTPException(status_code=403, detail="No autorizado")
    if notice_in.description is not None:
        notice.description = notice_in.description
    if notice_in.status is not None:
        notice.status = notice_in.status

    # Si ya está publicado, no se permite editar contenido
    if notice.status == NoticeStatus.PUBLISHED:
        raise HTTPException(
            409, "Un aviso publicado no se puede modificar. Crea uno nuevo."
        )
    # Aplicar cambios solo de los campos enviados
    update_data = notice_in.model_dump(exclude_unset=True, exclude={"publish"})
    for field, value in update_data.items():
        setattr(notice, field, value)
    # Si publish=True, hacer la transición
    if notice_in.publish:
        notice.status = NoticeStatus.PUBLISHED
        notice.published_at = datetime.utcnow()

    await db.commit()
    await db.refresh(notice)

    # Auditoría de actualización
    audit_logger.info(
        "notice.updated",
        extra={
            "notice_id": str(notice.id),
            "by": str(current_user.id),
            "updated_fields": [
                f
                for f in notice_in.model_fields_set
                if getattr(notice_in, f) is not None
            ],
        },
    )

    # Disparar el push a todos los usuarios. .delay() encola en Celery.
    dispatch_push.delay(str(notice.id))
    # SOLO si es CRÍTICO, programar el chequeo de fallback SMS a +60s.
    # Si es informativo o urgente, ESTA LÍNEA NO SE EJECUTA.
    # Esa es la regla clave de la lógica condicional del fallback.
    if notice.type == NoticeType.CRITICAL:
        schedule_sms_fallback.apply_async(
            args=[str(notice.id)],
            countdown=settings.SMS_FALLBACK_DELAY_SECONDS,
        )

    return _to_out(notice)


@router.delete("/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notice(
    notice_id: UUID,
    current_user: User = Depends(require_guard),
    db: AsyncSession = Depends(get_session),
):
    """Soft delete: marca el aviso como ARCHIVED. No se borra físicamente."""
    result = await db.execute(select(Notice).where(Notice.id == notice_id))
    notice = await db.get(Notice, notice_id)
    if not notice:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    if (
        notice.created_by != current_user.id
        and current_user.role != UserRole.SUPERADMIN
    ):
        raise HTTPException(status_code=403, detail="No autorizado")
    await db.delete(notice)
    await db.commit()

    audit_logger.info(
        "notice.archived",
        extra={"notice_id": str(notice.id), "by": str(current_user.id)},
    )


@router.post("/{notice_id}/media", response_model=NoticeOut)
async def upload_media(
    notice_id: UUID,
    file: UploadFile = File(...),
    kind: str = Form(...),  # "image" | "video"
    user: User = Depends(require_guard),
    db: AsyncSession = Depends(get_session),
):
    """Sube imagen o vídeo y lo asocia al aviso. Solo borradores."""
    if kind not in ("image", "video"):
        raise HTTPException(400, "kind debe ser 'image' o 'video'")
    notice = await db.get(Notice, notice_id)
    if notice is None or notice.status != NoticeStatus.DRAFT:
        raise HTTPException(404, "Aviso no encontrado o ya publicado.")
    if notice.created_by != user.id and user.role != UserRole.SUPERADMIN:
        raise HTTPException(403, "No puedes modificar este aviso.")
    # Leer el archivo entero a memoria. Para archivos grandes (vídeo de 100MB)
    # conviene streaming, pero por simplicidad lo leemos completo aquí.
    contents = await file.read()
    try:
        key = media_service.upload(contents, file.filename or "media", kind)
    except ValueError as e:
        raise HTTPException(400, str(e))
    # Append al array. SQLAlchemy + ARRAY no detecta in-place mutations
    # bien, así que asignamos una lista nueva.
    notice.media_keys = list(notice.media_keys) + [key]
    await db.commit()
    await db.refresh(notice)
    return _to_out(notice)
