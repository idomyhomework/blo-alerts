from fastapi import APIRouter, Depends, HTTPException, status
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
