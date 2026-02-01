"""DuckDB database service for H3 data."""

from pathlib import Path
from typing import Any

import duckdb

from h3_api.config import settings


class DatabaseService:
    """Service for querying H3 data from DuckDB."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or settings.database_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path), read_only=True)
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_h3_cells_in_bbox(
        self,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        resolution: int = 9,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """Get H3 cells within a bounding box."""
        conn = self.connect()

        # Query mart.h3_cells or similar table from g-etl
        # Adjust table/column names based on your g-etl schema
        query = """
        SELECT
            h3_cell,
            klass,
            leverantor,
            COUNT(*) as count
        FROM mart.h3_cells
        WHERE h3_get_resolution(h3_cell) = ?
        GROUP BY h3_cell, klass, leverantor
        LIMIT ?
        """

        try:
            result = conn.execute(query, [resolution, limit]).fetchall()
            return [
                {
                    "h3_cell": row[0],
                    "klass": row[1],
                    "leverantor": row[2],
                    "count": row[3],
                }
                for row in result
            ]
        except duckdb.CatalogException:
            # Table doesn't exist - return empty
            return []

    def get_cell_details(self, cell_id: str) -> dict[str, Any] | None:
        """Get details for a specific H3 cell."""
        conn = self.connect()

        query = """
        SELECT
            h3_cell,
            klass,
            leverantor,
            COUNT(*) as count
        FROM mart.h3_cells
        WHERE h3_cell = ?
        GROUP BY h3_cell, klass, leverantor
        """

        try:
            result = conn.execute(query, [cell_id]).fetchone()
            if result:
                return {
                    "h3_cell": result[0],
                    "klass": result[1],
                    "leverantor": result[2],
                    "count": result[3],
                }
            return None
        except duckdb.CatalogException:
            return None

    def list_tables(self) -> list[str]:
        """List available tables in mart schema."""
        conn = self.connect()
        try:
            result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'mart'"
            ).fetchall()
            return [row[0] for row in result]
        except Exception:
            return []


# Singleton instance
_db_service: DatabaseService | None = None


def get_db() -> DatabaseService:
    """Get database service singleton."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
