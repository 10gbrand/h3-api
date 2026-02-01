"""Configuration for H3 API."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_path: Path = Path("../g-etl/data/warehouse.duckdb")

    # API
    api_title: str = "H3 API"
    api_description: str = "FastAPI service for H3 hexbin/heatmap data"
    api_version: str = "0.1.0"

    # Limits
    max_cells_per_request: int = 10000
    default_resolution: int = 9

    # CORS
    cors_origins: list[str] = ["*"]

    model_config = {"env_prefix": "H3_API_"}


settings = Settings()
