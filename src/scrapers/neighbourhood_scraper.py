"""
Neighbourhood Boundary Scraper — Gets REAL neighbourhood polygons from Regina GIS.

Data Source (PRIMARY — LIVE):
  City of Regina ArcGIS Feature Service — Subdivision Boundaries
  URL: https://services6.arcgis.com/EXgfJNbcrqacNMPa/arcgis/rest/services/shp_Subdivisions/FeatureServer/0/query
  Returns actual polygon GeoJSON with SUB_NAME field

Fallback: centroid-based approximate hexagonal polygons

Output: data/processed/neighbourhoods.geojson
"""

import asyncio
import json
import logging
import math
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Live ArcGIS endpoint for subdivision boundaries
BOUNDARIES_API_URL = (
    "https://services6.arcgis.com/EXgfJNbcrqacNMPa/arcgis/rest/services/"
    "shp_Subdivisions/FeatureServer/0/query"
)


class NeighbourhoodScraper:
    """Collects real neighbourhood boundary polygons from City of Regina GIS."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self):
        """Collect neighbourhood boundaries from live GIS API."""
        logger.info("Starting neighbourhood boundary collection (LIVE GIS)...")

        # PRIMARY: Fetch real polygons from ArcGIS
        boundaries = await self._fetch_live_boundaries()

        if boundaries:
            logger.info(f"  Got {len(boundaries)} REAL boundary polygons from City of Regina GIS")
            source = "city_of_regina_gis"
        else:
            # FALLBACK: centroid-based approximation
            logger.warning("  Live GIS failed — using centroid approximation fallback")
            boundaries = self._create_from_centroids()
            source = "centroid_approximation"

        # Write output
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_neighbourhoods": len(boundaries),
                "city": "Regina",
                "province": "Saskatchewan",
                "source": source,
                "source_url": BOUNDARIES_API_URL,
            },
            "features": boundaries,
        }

        output_path = self.processed_dir / "neighbourhoods.geojson"
        output_path.write_text(json.dumps(geojson, indent=2))
        logger.info(f"  Written {len(boundaries)} neighbourhood boundaries to {output_path}")

    async def _fetch_live_boundaries(self) -> list[dict] | None:
        """Fetch real boundary polygons from City of Regina ArcGIS service."""
        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": "4326",
            "f": "geojson",
            "resultRecordCount": 200,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(BOUNDARIES_API_URL, params=params)

                if response.status_code != 200:
                    logger.warning(f"  Boundaries API returned HTTP {response.status_code}")
                    return None

                data = response.json()
                features = data.get("features", [])

                if not features:
                    logger.warning("  Boundaries API returned empty features")
                    return None

                # Save raw response
                raw_path = self.raw_dir / "subdivisions_raw.geojson"
                raw_path.write_text(json.dumps(data, indent=2))

                # Process: normalize field names
                processed = []
                for feature in features:
                    props = feature.get("properties", {})
                    geometry = feature.get("geometry")

                    if not geometry:
                        continue

                    # Extract the subdivision name (field is SUB_NAME)
                    name = (
                        props.get("SUB_NAME")
                        or props.get("sub_name")
                        or props.get("Name")
                        or props.get("NAME")
                        or "Unknown"
                    )

                    # Build normalized feature
                    normalized = {
                        "type": "Feature",
                        "geometry": geometry,
                        "properties": {
                            "name": name,
                            "source": "city_of_regina_gis",
                        },
                    }

                    # Carry over any other useful fields
                    for key in ("OBJECTID", "Shape__Area", "Shape__Length"):
                        if key in props:
                            normalized["properties"][key.lower()] = props[key]

                    processed.append(normalized)

                return processed if processed else None

        except httpx.TimeoutException:
            logger.warning("  Boundaries API timed out")
            return None
        except Exception as e:
            logger.warning(f"  Boundaries API error: {e}")
            return None

    def _create_from_centroids(self) -> list[dict]:
        """
        Create approximate neighbourhood polygons from centroids.
        Uses a hexagonal approximation — fallback when GIS API is unavailable.
        """
        from .crime_scraper import NEIGHBOURHOOD_CENTROIDS

        features = []
        # Approximate radius for a Regina neighbourhood (~600m)
        radius_deg = 0.006

        for name, (lat, lon) in NEIGHBOURHOOD_CENTROIDS.items():
            # Skip alternate names that duplicate real neighbourhoods
            if name in ("Core Group", "Transitional", "Walsh Acres Industrial",
                        "Warehouse District"):
                continue

            # Create hexagon approximation
            coords = []
            for i in range(6):
                angle = (2 * math.pi * i) / 6 + (math.pi / 6)  # Flat-top hex
                point_lon = lon + radius_deg * math.cos(angle)
                # Adjust for latitude (lon degrees are smaller at higher latitudes)
                point_lat = lat + radius_deg * 0.65 * math.sin(angle)
                coords.append([round(point_lon, 6), round(point_lat, 6)])
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
