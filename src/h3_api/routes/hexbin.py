"""Hexbin endpoint for H3 data."""

import h3
from fastapi import APIRouter, HTTPException, Path, Query
from h3 import LatLngPoly

from h3_api.config import settings
from h3_api.models import Feature, FeatureCollection, HexProperties
from h3_api.services import get_db

router = APIRouter(prefix="/hexbin", tags=["hexbin"])


def cell_to_polygon(cell: str) -> dict:
    """Convert H3 cell to GeoJSON polygon."""
    # h3 v4 returns (lat, lng) tuples, GeoJSON needs [lng, lat]
    boundary = h3.cell_to_boundary(cell)
    coords = [[lng, lat] for lat, lng in boundary]
    # Close the polygon ring
    coords.append(coords[0])
    return {"type": "Polygon", "coordinates": [coords]}


@router.get("/layers")
async def get_layers() -> list[dict]:
    """
    Get list of available layers with cell counts.

    Returns list of layer names that can be used with the hexbin endpoint.
    """
    db = get_db()
    return db.get_available_layers()


@router.get("/raw")
async def get_hexbin_raw(
    bbox: str = Query(
        ...,
        description="Bounding box: minLng,minLat,maxLng,maxLat",
        example="17.9,59.3,18.1,59.4",
    ),
    res: int = Query(
        default=settings.default_resolution,
        ge=0,
        le=15,
        description="H3 resolution (0-15)",
        example=9,
    ),
    layer: str = Query(
        ...,
        description="Layer name (use /hexbin/layers to see available)",
        example="naturreservat",
    ),
    limit: int = Query(
        default=settings.max_cells_per_request,
        le=settings.max_cells_per_request,
        description="Max cells to return",
        example=1000,
    ),
) -> dict:
    """
    Get raw H3 cell data (optimized for deck.gl).

    Returns compact JSON without GeoJSON overhead.
    """
    try:
        min_lng, min_lat, max_lng, max_lat = map(float, bbox.split(","))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bbox format")

    db = get_db()
    rows = db.get_h3_cells_in_bbox(
        min_lng, min_lat, max_lng, max_lat, res, limit, layers=[layer]
    )

    # Return compact format for deck.gl
    return {
        "cells": [{"h": r["h3_cell"], "c": r["count"]} for r in rows],
        "layer": layer,
        "resolution": res,
        "count": len(rows),
    }


@router.get("/fast/{layer}")
async def get_hexbin_fast(
    layer: str = Path(
        ...,
        description="Layer name",
        example="naturreservat",
    ),
    bbox: str = Query(
        None,
        description="Bounding box (optional): minLng,minLat,maxLng,maxLat",
        example="17.9,59.3,18.1,59.4",
    ),
) -> dict:
    """
    Get all H3 cells for a layer at res-8 (optimized for deck.gl).

    Uses pre-aggregated tables for instant response.
    deck.gl handles rendering/aggregation on client.
    """
    db = get_db()
    conn = db.connect()

    table = f"mart.h3_{layer}_r8"

    try:
        if bbox:
            min_lng, min_lat, max_lng, max_lat = map(float, bbox.split(","))
            query = f"""
            SELECT h3, count FROM {table}
            WHERE lat BETWEEN {min_lat} AND {max_lat}
              AND lng BETWEEN {min_lng} AND {max_lng}
            """
        else:
            query = f"SELECT h3, count FROM {table}"

        result = conn.execute(query).fetchall()

        return {
            "cells": [{"h": r[0], "c": r[1]} for r in result],
            "layer": layer,
            "resolution": 8,
            "count": len(result),
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Layer not found: {layer}")


@router.get("", response_model=FeatureCollection)
async def get_hexbin(
    bbox: str = Query(
        ...,
        description="Bounding box: minLng,minLat,maxLng,maxLat",
        example="17.9,59.3,18.1,59.4",
    ),
    res: int = Query(
        default=settings.default_resolution,
        ge=0,
        le=15,
        description="H3 resolution (0-15)",
        example=9,
    ),
    layer: str = Query(
        default=None,
        description="Layer name (use /hexbin/layers to see available layers)",
        example="naturreservat",
    ),
    limit: int = Query(
        default=settings.max_cells_per_request,
        le=settings.max_cells_per_request,
        description="Max cells to return",
        example=1000,
    ),
) -> FeatureCollection:
    """
    Get H3 hexbins for a bounding box.

    Returns GeoJSON FeatureCollection with hex polygons and aggregated counts.
    Optionally filter by layer name.
    """
    try:
        min_lng, min_lat, max_lng, max_lat = map(float, bbox.split(","))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid bbox format. Expected: minLng,minLat,maxLng,maxLat",
        )

    # Get cells from database
    db = get_db()
    layers = [layer] if layer else None
    rows = db.get_h3_cells_in_bbox(min_lng, min_lat, max_lng, max_lat, res, limit, layers=layers)

    # Convert to GeoJSON features
    features = []
    for row in rows:
        try:
            features.append(
                Feature(
                    geometry=cell_to_polygon(row["h3_cell"]),
                    properties=HexProperties(
                        cell=row["h3_cell"],
                        resolution=res,
                        count=row["count"],
                        klass=row.get("layer"),
                        leverantor=row.get("leverantor"),
                    ),
                )
            )
        except Exception:
            # Skip invalid cells
            continue

    return FeatureCollection(features=features)


@router.get("/viewport", response_model=FeatureCollection)
async def get_hexbin_viewport(
    bbox: str = Query(
        ...,
        description="Bounding box: minLng,minLat,maxLng,maxLat",
        example="18.0,59.3,18.1,59.35",
    ),
    res: int = Query(
        default=settings.default_resolution,
        ge=0,
        le=15,
        description="H3 resolution (0-15)",
        example=9,
    ),
) -> FeatureCollection:
    """
    Get empty H3 grid for a viewport (for overlay).

    Returns hex grid without data - useful for showing coverage area.
    """
    try:
        min_lng, min_lat, max_lng, max_lat = map(float, bbox.split(","))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bbox format")

    # Create viewport polygon using h3 v4 LatLngPoly (lat, lng order)
    poly = LatLngPoly(
        [
            (min_lat, min_lng),
            (max_lat, min_lng),
            (max_lat, max_lng),
            (min_lat, max_lng),
        ]
    )

    # Get cells covering viewport
    cells = list(h3.polygon_to_cells(poly, res))

    # Limit to prevent huge responses
    if len(cells) > settings.max_cells_per_request:
        cells = cells[: settings.max_cells_per_request]

    features = [
        Feature(
            geometry=cell_to_polygon(cell),
            properties=HexProperties(cell=cell, resolution=res, count=0),
        )
        for cell in cells
    ]

    return FeatureCollection(features=features)


@router.get("/cell/{cell_id}")
async def get_cell(
    cell_id: str = Path(
        ...,
        description="H3 cell ID",
        example="891e0e4d253ffff",
    ),
) -> dict:
    """
    Get details for a specific H3 cell.

    Useful for debugging and inspecting individual cells.
    """
    if not h3.is_valid_cell(cell_id):
        raise HTTPException(status_code=400, detail="Invalid H3 cell ID")

    # Get cell info (h3 v4 returns lat, lng tuples)
    boundary_raw = h3.cell_to_boundary(cell_id)
    boundary = [[lng, lat] for lat, lng in boundary_raw]
    boundary.append(boundary[0])  # Close the ring
    center = h3.cell_to_latlng(cell_id)
    resolution = h3.get_resolution(cell_id)
    neighbors = list(h3.grid_ring(cell_id, 1))

    # Get data from database
    db = get_db()
    data = db.get_cell_details(cell_id)

    return {
        "cell_id": cell_id,
        "resolution": resolution,
        "center": {"lat": center[0], "lng": center[1]},
        "boundary": {"type": "Polygon", "coordinates": [boundary]},
        "neighbors": neighbors,
        "data": data,
    }
