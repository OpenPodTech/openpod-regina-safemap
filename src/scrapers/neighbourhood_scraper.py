"""
Neighbourhood Boundary Scraper — Gets neighbourhood polygons for Regina.

Data Sources:
1. OpenRegina.ca — Official neighbourhood boundary datasets
2. City of Regina GIS — opengis.regina.ca
3. OpenStreetMap — admin boundaries as fallback

Output: data/processed/neighbourhoods.geojson
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# OpenRegina CKAN API base URL
OPEN_REGINA_API = "https://openregina.ca/api/3/action"

# Known City of Regina GIS endpoints
REGINA_GIS_ENDPOINTS = [
    "https://opengis.regina.ca/arcgis/rest/services/OpenData/MapServer",
    "https://services.arcgis.com/VsaNWYRmqJifbHjB/arcgis/rest/services",
]


class NeighbourhoodScraper:
    """Collects neighbourhood boundary polygons for Regina."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self):
        """Try multiple sources for neighbourhood boundaries."""
        logger.info("Starting neighbourhood boundary collection...")

        # Try OpenRegina first
        boundaries = await self.collect_from_openregina()

        # Fallback to GIS endpoint
        if not boundaries:
            boundaries = await self.collect_from_gis()

        # Fallback to OSM admin boundaries
        if not boundaries:
            boundaries = await self.collect_from_osm()

        # Final fallback: use our hardcoded centroid data to create placeholder polygons
        if not boundaries:
            logger.warning("  All boundary sources failed — using centroid approximations")
            boundaries = self._create_from_centroids()

        # Write output
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_neighbourhoods": len(boundaries),
                "city": "Regina",
                "province": "Saskatchewan",
            },
            "features": boundaries,
        }

        output_path = self.processed_dir / "neighbourhoods.geojson"
        output_path.write_text(json.dumps(geojson, indent=2))
        logger.info(f"  Written {len(boundaries)} neighbourhood boundaries to {output_path}")

    async def collect_from_openregina(self) -> list[dict] | None:
        """Search OpenRegina.ca CKAN for neighbourhood boundary datasets."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Search for neighbourhood datasets
                response = await client.get(
                    f"{OPEN_REGINA_API}/package_search",
                    params={"q": "neighbourhood boundary", "rows": 10},
                )

                if response.status_code != 200:
                    logger.warning(f"  OpenRegina search failed: HTTP {response.status_code}")
                    return None

                data = response.json()
                results = data.get("result", {}).get("results", [])

                for dataset in results:
                    resources = dataset.get("resources", [])
                    for resource in resources:
                        fmt = resource.get("format", "").lower()
                        if fmt in ("geojson", "json", "shp"):
                            url = resource.get("url")
                            if url:
                                logger.info(f"  Found boundary dataset: {dataset.get('title')}")
                                return await self._fetch_geojson_resource(client, url)

                logger.info("  No GeoJSON boundary dataset found on OpenRegina")
                return None

            except Exception as e:
                logger.warning(f"  OpenRegina search failed: {e}")
                return None

    async def _fetch_geojson_resource(self, client: httpx.AsyncClient, url: str) -> list[dict] | None:
        """Fetch and parse a GeoJSON resource URL."""
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()

                # Save raw
                raw_path = self.raw_dir / "neighbourhoods_openregina.geojson"
                raw_path.write_text(json.dumps(data, indent=2))

                features = data.get("features", [])
                if features:
                    return features
            return None
        except Exception as e:
            logger.warning(f"  Failed to fetch GeoJSON resource: {e}")
            return None

    async def collect_from_gis(self) -> list[dict] | None:
        """Try City of Regina ArcGIS REST endpoints for neighbourhood layers."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            for base_url in REGINA_GIS_ENDPOINTS:
                try:
                    # Query for neighbourhood feature layer
                    query_url = f"{base_url}/0/query"
                    params = {
                        "where": "1=1",
                        "outFields": "*",
                        "outSR": "4326",
                        "f": "geojson",
                        "resultRecordCount": 200,
                    }

                    response = await client.get(query_url, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        features = data.get("features", [])
                        if features:
                            logger.info(f"  Fetched {len(features)} boundaries from GIS")
                            # Save raw
                            raw_path = self.raw_dir / "neighbourhoods_gis.geojson"
                            raw_path.write_text(json.dumps(data, indent=2))
                            return features

                except Exception as e:
                    logger.debug(f"  GIS endpoint failed ({base_url}): {e}")

        return None

    async def collect_from_osm(self) -> list[dict] | None:
        """Fetch neighbourhood boundaries from OpenStreetMap."""
        query = """
        [out:json][timeout:120];
        area["name"="Regina"]["admin_level"="8"]->.regina;
        (
          relation["boundary"="administrative"]["admin_level"="10"](area.regina);
          relation["place"="neighbourhood"](area.regina);
          relation["place"="suburb"](area.regina);
        );
        out geom;
        """

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://overpass-api.de/api/interpreter",
                    data={"data": query},
                )
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get("elements", [])

                    if elements:
                        logger.info(f"  Fetched {len(elements)} boundaries from OSM")
                        features = self._osm_to_geojson_features(elements)
                        if features:
                            return features

            except Exception as e:
                logger.warning(f"  OSM boundary query failed: {e}")

        return None

    def _osm_to_geojson_features(self, elements: list) -> list[dict]:
        """Convert OSM relation elements to GeoJSON features."""
        features = []

        for element in elements:
            if element.get("type") != "relation":
                continue

            tags = element.get("tags", {})
            name = tags.get("name", "Unknown")

            # Extract outer ring from members
            members = element.get("members", [])
            outer_coords = []

            for member in members:
                if member.get("role") == "outer" and "geometry" in member:
                    for point in member["geometry"]:
                        outer_coords.append([point["lon"], point["lat"]])

            if outer_coords:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [outer_coords],
                    },
                    "properties": {
                        "name": name,
                        "osm_id": element.get("id"),
                    },
                })

        return features

    def _create_from_centroids(self) -> list[dict]:
        """
        Create approximate neighbourhood polygons from centroids.
        Uses a simple circle approximation — good enough for display
        until we get real boundaries.
        """
        import math

        from ..scrapers.crime_scraper import NEIGHBOURHOOD_CENTROIDS

        features = []
        # Approximate radius of a Regina neighbourhood (~500m)
        radius_deg = 0.005  # ~500m at this latitude

        for name, (lat, lon) in NEIGHBOURHOOD_CENTROIDS.items():
            # Create octagon approximation
            coords = []
            for i in range(8):
                angle = (2 * math.pi * i) / 8
                point_lon = lon + radius_deg * math.cos(angle)
                point_lat = lat + radius_deg * 0.7 * math.sin(angle)  # Adjust for lat
                coords.append([point_lon, point_lat])
            coords.append(coords[0])  # Close the polygon

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords],
                },
                "properties": {
                    "name": name,
                    "source": "centroid_approximation",
                    "note": "Approximate boundary — replace with official GIS data",
                },
            })

        return features


async def main():
    """Run neighbourhood scraper standalone."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = NeighbourhoodScraper()
    await scraper.collect_all()


if __name__ == "__main__":
    asyncio.run(main())
