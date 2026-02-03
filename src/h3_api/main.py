"""H3 API - FastAPI application for hexbin/heatmap data."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from h3_api.config import settings
from h3_api.routes import health_router, hexbin_router
from h3_api.services import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup: verify database connection
    db = get_db()
    db.connect()
    yield
    # Shutdown: close database
    db.close()


app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(hexbin_router)


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "endpoints": {
            "hexbin": "/hexbin?bbox=minLng,minLat,maxLng,maxLat&res=9",
            "viewport": "/hexbin/viewport?bbox=...&res=9",
            "cell": "/hexbin/cell/{cell_id}",
            "health": "/health",
            "ready": "/ready",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("h3_api.main:app", host="0.0.0.0", port=8000, reload=True)
