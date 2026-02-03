"""API routes for H3 API."""

from .health import router as health_router
from .hexbin import router as hexbin_router

__all__ = ["hexbin_router", "health_router"]
