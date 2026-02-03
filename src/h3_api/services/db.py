"""DuckDB database service for H3 data."""

from pathlib import Path
from typing import Any

import duckdb

from h3_api.config import settings

# Tables that contain H3 cell data (exclude compact_ versions)
H3_TABLES = [
    "naturreservat",
    "nationalparker",
    "biotopskydd",
    "kulturreservat",
    "naturminnen_punkt",
    "naturminnen_ytor",
    "naturvardsavtal",
    "Naturvardsomrade",
    "ramsar_vatmarker",
    "skyddsvarda_statliga_skogar",
    "natura2000_spa",
    "natura2000_sci_ac",
    "natura2000_sci_alvar_bd",
    "natura2000_sci_ej_alvar_rikstackande",
    "vso",
]


class DatabaseService:
    """Service for querying H3 data from DuckDB."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or settings.database_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path), read_only=True)
            # Load H3 extension
            self._conn.execute("INSTALL h3 FROM community; LOAD h3;")
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def get_available_layers(self) -> list[dict[str, Any]]:
        """Get list of available layers with row counts."""
        conn = self.connect()
        layers = []
        for table in H3_TABLES:
            try:
                result = conn.execute(
                    f"SELECT COUNT(*) FROM mart.{table} WHERE h3_cell IS NOT NULL"
                ).fetchone()
                count = result[0] if result else 0
                if count > 0:
                    layers.append({"name": table, "count": count})
            except duckdb.CatalogException:
                continue
        return layers

    def get_h3_cells_for_layer(
        self,
        layer: str,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        resolution: int = 9,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        """Get H3 cells for a layer within a bounding box, aggregated to resolution."""
        if layer not in H3_TABLES:
            return []

        conn = self.connect()

        # Data is stored at resolution 11, we need to aggregate to requested resolution
        # Use h3_cell_to_parent to convert to requested resolution
        query = f"""
        SELECT
            h3_h3_to_string(
                h3_cell_to_parent(h3_string_to_h3(h3_cell), {resolution})
            ) as parent_cell,
            COUNT(*) as count
        FROM mart.{layer}
        WHERE h3_cell IS NOT NULL
        GROUP BY parent_cell
        LIMIT {limit}
        """

        try:
            result = conn.execute(query).fetchall()
            return [
                {
                    "h3_cell": row[0],
                    "count": row[1],
                    "layer": layer,
                }
                for row in result
            ]
        except Exception:
            return []

    def get_h3_cells_in_bbox(
        self,
        min_lng: float,
        min_lat: float,
        max_lng: float,
        max_lat: float,
        resolution: int = 9,
        limit: int = 10000,
        layers: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get H3 cells within a bounding box from specified layers."""
        if layers is None:
            layers = H3_TABLES

        conn = self.connect()
        all_results = []

        for layer in layers:
            if layer not in H3_TABLES:
                continue

            # Try pre-aggregated table first (much faster)
            agg_table = f"mart.h3_agg_{layer}_r{resolution}"
            try:
                query = f"""
                SELECT h3_cell, count
                FROM {agg_table}
                WHERE lat BETWEEN {min_lat} AND {max_lat}
                  AND lng BETWEEN {min_lng} AND {max_lng}
                LIMIT {limit}
                """
                result = conn.execute(query).fetchall()
                for row in result:
                    all_results.append(
                        {"h3_cell": row[0], "count": row[1], "layer": layer}
                    )
                continue  # Success, skip fallback
            except Exception:
                pass  # Table doesn't exist, use fallback

            # Fallback: aggregate on-the-fly (slower)
            query = f"""
            WITH filtered AS (
                SELECT h3_cell
                FROM mart.{layer}
                WHERE h3_cell IS NOT NULL
                  AND h3_cell_to_lat(h3_string_to_h3(h3_cell)) BETWEEN {min_lat} AND {max_lat}
                  AND h3_cell_to_lng(h3_string_to_h3(h3_cell)) BETWEEN {min_lng} AND {max_lng}
            )
            SELECT
                h3_h3_to_string(
                    h3_cell_to_parent(h3_string_to_h3(h3_cell), {resolution})
                ) as parent_cell,
                COUNT(*) as count
            FROM filtered
            GROUP BY parent_cell
            LIMIT {limit}
            """

            try:
                result = conn.execute(query).fetchall()
                for row in result:
                    all_results.append(
                        {"h3_cell": row[0], "count": row[1], "layer": layer}
                    )
            except Exception:
                continue

        return all_results[:limit]

    def get_cell_details(self, cell_id: str, layer: str | None = None) -> dict[str, Any] | None:
        """Get details for a specific H3 cell."""
        conn = self.connect()

        layers_to_check = [layer] if layer and layer in H3_TABLES else H3_TABLES
        results = {}

        for table in layers_to_check:
            try:
                # Check if the cell or any of its children exist in this layer
                query = f"""
                SELECT COUNT(*) as count
                FROM mart.{table}
                WHERE h3_cell IS NOT NULL
                  AND h3_h3_to_string(
                      h3_cell_to_parent(
                          h3_string_to_h3(h3_cell),
                          h3_get_resolution(h3_string_to_h3('{cell_id}'))
                      )
                  ) = '{cell_id}'
                """
                result = conn.execute(query).fetchone()
                if result and result[0] > 0:
                    results[table] = result[0]
            except Exception:
                continue

        if results:
            return {"cell_id": cell_id, "layers": results, "total": sum(results.values())}
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
