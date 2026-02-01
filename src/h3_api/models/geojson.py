"""GeoJSON Pydantic models for H3 hexbin responses."""

from typing import Any, Literal

from pydantic import BaseModel


class HexProperties(BaseModel):
    """Properties for a hex cell feature."""

    cell: str
    resolution: int
    count: int = 0
    klass: str | None = None
    leverantor: str | None = None


class Feature(BaseModel):
    """GeoJSON Feature."""

    type: Literal["Feature"] = "Feature"
    geometry: dict[str, Any]
    properties: HexProperties


class FeatureCollection(BaseModel):
    """GeoJSON FeatureCollection."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[Feature]
