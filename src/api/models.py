"""
Data models for the SafeMap API.
"""

from pydantic import BaseModel
from typing import Optional


class NeighbourhoodScore(BaseModel):
    """Score summary for a neighbourhood."""
    name: str
    overall: int
    grade: str
    safety: int
    schools: int
    transit: int
    amenities: int
    walkability: int
    total_crimes: int = 0
    crime_trend: float = 0.0
    schools_count: int = 0
    transit_stops: int = 0
    grocery_count: int = 0
    healthcare_count: int = 0
    parks_count: int = 0
    community_count: int = 0


class NeighbourhoodSummary(BaseModel):
    """Brief neighbourhood info for search results."""
    name: str
    overall: int
    grade: str
    lat: Optional[float] = None
    lon: Optional[float] = None


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "ok"
    version: str = "0.1.0"
    project: str = "openpod-regina-safemap"
    data_loaded: bool = False
    neighbourhoods: int = 0
    crimes: int = 0
