import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db

router = APIRouter()
log = logging.getLogger(__name__)

CHECK_SQL = "SELECT 1"


@router.get("/health")
def health(db: Session = Depends(get_db)) -> JSONResponse:
    try:
        ms = int(get_settings().health_timeout_ms)
        db.execute(text(f"SET LOCAL statement_timeout = {ms}"))
        db.execute(text(CHECK_SQL))
    except Exception as exc:
        log.error("health check failed: %s", type(exc).__name__)
        return JSONResponse({"status": "degraded", "db": "down"}, status_code=503)
    return JSONResponse({"status": "ok", "db": "ok"})
