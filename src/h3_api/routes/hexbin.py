"""Hexbin endpoint for H3 data."""

import h3
from fastapi import APIRouter, HTTPException, Query
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


@router.get("", response_model=FeatureCollection)
async def get_hexbin(
    bbox: str = Query(
        ...,
        description="Bounding box: minLng,minLat,maxLng,maxLat",
        examples=["11.0,55.0,24.0,69.0"],
    ),
    res: int = Query(
        default=settings.default_resolution,
        ge=0,
        le=15,
        description="H3 resolution (0-15)",
    ),
    limit: int = Query(
        default=settings.max_cells_per_request,
        le=settings.max_cells_per_request,
        description="Max cells to return",
    ),
) -> FeatureCollection:
    """
    Get H3 hexbins for a bounding box.

    Returns GeoJSON FeatureCollection with hex polygons and aggregated counts.
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
    rows = db.get_h3_cells_in_bbox(min_lng, min_lat, max_lng, max_lat, res, limit)

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
                        klass=row.get("klass"),
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
    bbox: str = Query(..., description="Bounding box: minLng,minLat,maxLng,maxLat"),
    res: int = Query(default=settings.default_resolution, ge=0, le=15),
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
async def get_cell(cell_id: str) -> dict:
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
