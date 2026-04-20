from __future__ import annotations

from app.core.config import settings

try:
    from celery import Celery
except Exception:  # pragma: no cover - optional runtime dependency
    Celery = None  # type: ignore[assignment]


def _build_celery():
    if Celery is None:
        return None
    app = Celery(
        "zhixi_worker",
        broker=settings.REDIS_BROKER_URL,
        backend=settings.REDIS_RESULT_BACKEND,
        include=["app.worker.tasks"],
    )
    app.conf.update(
        task_track_started=True,
        worker_concurrency=1,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )
    return app


celery = _build_celery()


def celery_enabled() -> bool:
    return bool(celery is not None and settings.DIGITAL_HUMAN_CELERY_ENABLED)
