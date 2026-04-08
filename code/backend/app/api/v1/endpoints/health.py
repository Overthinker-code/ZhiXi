from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.db import engine

router = APIRouter()


@router.get('/healthz')
def healthz():
    return {'service': 'backend', 'status': 'ok'}


@router.get('/readyz')
def readyz():
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {'service': 'backend', 'status': 'ready', 'db': 'ok'}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'ready check failed: {exc}')
