"""API routes for H3 API."""

from .hexbin import router as hexbin_router
from .health import router as health_router

__all__ = ["hexbin_router", "health_router"]
