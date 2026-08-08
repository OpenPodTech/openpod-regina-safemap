"""
Regina SafeMap — FastAPI Backend

Serves neighbourhood data, crime GeoJSON, scores, and search
to the Leaflet.js frontend.

Usage:
    uvicorn src.api.main:app --reload --port 8000

Endpoints:
    GET /api/health              — Health check
    GET /api/neighbourhoods      — GeoJSON boundaries (with scores if available)
    GET /api/crimes              — Crime GeoJSON for heatmap
    GET /api/schools             — Schools GeoJSON
    GET /api/transit             — Transit stops GeoJSON
    GET /api/amenities           — Amenities GeoJSON
    GET /api/parks               — Parks GeoJSON
    GET /api/scores              — All neighbourhood scores as JSON
    GET /api/scores/{name}       — Score for a specific neighbourhood
    GET /api/search?q=           — Search neighbourhoods by name
"""

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .models import HealthResponse, NeighbourhoodScore, NeighbourhoodSummary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("safemap.api")

# ─── App Setup ────────────────────────────────────────────────────

app = FastAPI(
    title="Regina SafeMap API",
    description="Neighbourhood intelligence API for Regina, Saskatchewan. Open data, open source.",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — allow frontend to call API from any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Data Store ───────────────────────────────────────────────────

DATA_DIR = Path("data/processed")

# In-memory cache of loaded GeoJSON data
_cache = {
    "neighbourhoods": None,
    "crimes": None,
    "schools": None,
    "transit_stops": None,
    "amenities": None,
    "parks": None,
    "scores": None,
}


def _load_geojson(filename: str) -> Optional[dict]:
    """Load a GeoJSON file from the data directory."""
    path = DATA_DIR / filename
    if path.exists():
        return json.loads(path.read_text())
    return None


def _load_all_data():
    """Load all data files into memory cache."""
    # Prefer scored neighbourhoods if available
    _cache["neighbourhoods"] = (
        _load_geojson("neighbourhoods_scored.geojson")
        or _load_geojson("neighbourhoods.geojson")
    )
    _cache["crimes"] = _load_geojson("crimes.geojson")
    _cache["schools"] = _load_geojson("schools.geojson")
    _cache["transit_stops"] = _load_geojson("transit_stops.geojson")
    _cache["amenities"] = _load_geojson("amenities.geojson")
    _cache["parks"] = _load_geojson("parks.geojson")

    # Load scores JSON
    scores_path = DATA_DIR / "scores.json"
    if scores_path.exists():
        _cache["scores"] = json.loads(scores_path.read_text())

    loaded = sum(1 for v in _cache.values() if v is not None)
    logger.info(f"Loaded {loaded}/{len(_cache)} data files from {DATA_DIR}")


# ─── Startup Event ────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Load data on server start."""
    logger.info("Starting Regina SafeMap API...")
    _load_all_data()


# ─── API Routes ───────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check — shows data availability."""
    n_count = 0
    if _cache["neighbourhoods"]:
        n_count = len(_cache["neighbourhoods"].get("features", []))

    c_count = 0
    if _cache["crimes"]:
        c_count = len(_cache["crimes"].get("features", []))

    return HealthResponse(
        data_loaded=any(v is not None for v in _cache.values()),
        neighbourhoods=n_count,
        crimes=c_count,
    )


@app.get("/api/neighbourhoods")
async def get_neighbourhoods():
    """Return neighbourhood boundaries as GeoJSON (enriched with scores if available)."""
    data = _cache["neighbourhoods"]
    if not data:
        return _empty_geojson("No neighbourhood data. Run: python -m src.scrapers.collect_all")
    return JSONResponse(content=data)


@app.get("/api/crimes")
async def get_crimes(
    year: Optional[int] = Query(None, description="Filter by year"),
    crime_type: Optional[str] = Query(None, description="Filter by crime type"),
    neighbourhood: Optional[str] = Query(None, description="Filter by neighbourhood"),
):
    """Return crime data as GeoJSON for heatmap rendering."""
    data = _cache["crimes"]
    if not data:
        return _empty_geojson("No crime data. Run: python -m src.scrapers.collect_all")

    # Apply filters if provided
    if year or crime_type or neighbourhood:
        filtered_features = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            if year and props.get("year") != year:
                continue
            if crime_type and props.get("crime_type", "").lower() != crime_type.lower():
                continue
            if neighbourhood and neighbourhood.lower() not in props.get("neighbourhood", "").lower():
                continue
            filtered_features.append(feature)

        return JSONResponse(content={
            "type": "FeatureCollection",
            "features": filtered_features,
        })

    return JSONResponse(content=data)


@app.get("/api/schools")
async def get_schools():
    """Return schools as GeoJSON."""
    data = _cache["schools"]
    if not data:
        return _empty_geojson("No school data. Run: python -m src.scrapers.collect_all")
    return JSONResponse(content=data)


@app.get("/api/transit")
async def get_transit():
    """Return transit stops as GeoJSON."""
    data = _cache["transit_stops"]
    if not data:
        return _empty_geojson("No transit data. Run: python -m src.scrapers.collect_all")
    return JSONResponse(content=data)


@app.get("/api/amenities")
async def get_amenities(
    category: Optional[str] = Query(None, description="Filter: grocery, healthcare, community"),
):
    """Return amenities as GeoJSON, optionally filtered by category."""
    data = _cache["amenities"]
    if not data:
        return _empty_geojson("No amenity data. Run: python -m src.scrapers.collect_all")

    if category:
        filtered = [
            f for f in data.get("features", [])
            if f.get("properties", {}).get("category", "").lower() == category.lower()
        ]
        return JSONResponse(content={"type": "FeatureCollection", "features": filtered})

    return JSONResponse(content=data)


@app.get("/api/parks")
async def get_parks():
    """Return parks as GeoJSON."""
    data = _cache["parks"]
    if not data:
        return _empty_geojson("No park data. Run: python -m src.scrapers.collect_all")
    return JSONResponse(content=data)


@app.get("/api/scores")
async def get_scores():
    """Return all neighbourhood scores."""
    if _cache["scores"]:
        return JSONResponse(content=_cache["scores"])

    # Try to generate from neighbourhood data
    if _cache["neighbourhoods"]:
        features = _cache["neighbourhoods"].get("features", [])
        scores = []
        for f in features:
            props = f.get("properties", {})
            if "overall" in props:
                scores.append({
                    "name": props.get("name", ""),
                    "overall": props.get("overall", 0),
                    "grade": props.get("grade", "—"),
                    "safety": props.get("safety", 0),
                    "schools": props.get("schools", 0),
                    "transit": props.get("transit", 0),
                    "amenities": props.get("amenities", 0),
                    "walkability": props.get("walkability", 0),
                })
        if scores:
            return JSONResponse(content={"scores": scores})

    raise HTTPException(
        status_code=404,
        detail="No scores available. Run: python -m src.scoring.calculator",
    )


@app.get("/api/scores/{neighbourhood_name}")
async def get_neighbourhood_score(neighbourhood_name: str):
    """Get score for a specific neighbourhood."""
    scores_data = _cache.get("scores")
    if not scores_data:
        raise HTTPException(status_code=404, detail="Scores not calculated yet")

    for score in scores_data.get("scores", []):
        if score["name"].lower() == neighbourhood_name.lower():
            return JSONResponse(content=score)

    # Fuzzy match
    for score in scores_data.get("scores", []):
        if neighbourhood_name.lower() in score["name"].lower():
            return JSONResponse(content=score)

    raise HTTPException(status_code=404, detail=f"Neighbourhood '{neighbourhood_name}' not found")


@app.get("/api/search")
async def search_neighbourhoods(
    q: str = Query(..., min_length=2, description="Search query"),
):
    """Search neighbourhoods by name. Returns matching names with scores."""
    results = []

    if _cache["neighbourhoods"]:
        for feature in _cache["neighbourhoods"].get("features", []):
            props = feature.get("properties", {})
            name = props.get("name", "")

            if q.lower() in name.lower():
                # Get centroid for map positioning
                geom = feature.get("geometry", {})
                lat, lon = None, None
                if geom.get("type") == "Polygon":
                    coords = geom.get("coordinates", [[]])[0]
                    if coords:
                        lon = sum(c[0] for c in coords) / len(coords)
                        lat = sum(c[1] for c in coords) / len(coords)

                results.append({
                    "name": name,
                    "overall": props.get("overall", 0),
                    "grade": props.get("grade", "—"),
                    "lat": lat,
                    "lon": lon,
                })

    return JSONResponse(content={"query": q, "results": results})


@app.get("/api/refresh")
async def refresh_data():
    """Reload data from disk (useful after running scrapers)."""
    _load_all_data()
    return {"status": "ok", "message": "Data reloaded from disk"}


# ─── Serve Frontend ──────────────────────────────────────────────

# Mount frontend static files at root (after API routes)
frontend_path = Path("frontend")
if frontend_path.exists():
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")


# ─── Helpers ─────────────────────────────────────────────────────

def _empty_geojson(message: str) -> JSONResponse:
    """Return an empty GeoJSON with a message in metadata."""
    return JSONResponse(content={
        "type": "FeatureCollection",
        "metadata": {"message": message, "total_features": 0},
        "features": [],
    })
