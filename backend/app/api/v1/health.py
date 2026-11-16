from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    database_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_status = "unavailable"

    ok = database_status == "connected"
    payload = {
        "status": "ok" if ok else "degraded",
        "service": "mini-aws-api",
        "version": "0.1.0",
        "mode": "local",
        "database": database_status,
    }
    return payload if ok else JSONResponse(status_code=503, content=payload)
