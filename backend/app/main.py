import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.admin import router as admin_router
from app.api.destinations import router as destinations_router
from app.api.parking import router as parking_router
from app.api.routes import router as routes_router
from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.include_router(destinations_router)
app.include_router(parking_router)
app.include_router(routes_router)
app.include_router(admin_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable") from exc

    return {"status": "ok", "database": "connected"}
