"""Health check endpoints."""

from fastapi import APIRouter

from h3_api.services import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    """Readiness check - verifies database connection."""
    db = get_db()
    tables = db.list_tables()

    return {
        "status": "ok",
        "database": str(db.db_path),
        "tables": tables,
    }
