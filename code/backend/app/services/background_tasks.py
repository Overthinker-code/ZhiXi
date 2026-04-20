from __future__ import annotations

import logging

from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.services.user_memory_profile_service import user_memory_profile_service
from app.worker.celery_app import celery, celery_enabled

logger = logging.getLogger(__name__)


def schedule_memory_profile_refresh(user_id: str | None) -> None:
    if not user_id or not settings.MEMORY_PROFILE_AUTO_REFRESH:
        return
    if celery_enabled() and celery is not None:
        try:
            celery.send_task("memory_profile.refresh", args=[str(user_id)])
            return
        except OperationalError as exc:
            logger.warning("memory profile celery unavailable, fallback sync: %s", exc)
        except Exception as exc:
            logger.warning("memory profile enqueue failed, fallback sync: %s", exc)
    try:
        user_memory_profile_service.refresh_profile(str(user_id))
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("memory profile sync refresh failed: %s", exc)
