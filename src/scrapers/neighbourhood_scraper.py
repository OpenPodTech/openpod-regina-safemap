"""
Neighbourhood Boundary Scraper — Gets neighbourhood polygons for Regina.

Strategy: Use centroid-based approximate polygons directly. Official GIS boundary
endpoints are unreliable. The centroid approximation is good enough for display
and scoring — gives users a visual sense of each neighbourhood's area.

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


class NeighbourhoodScraper:
    """Collects neighbourhood boundary polygons for Regina."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self):
        """Collect neighbourhood boundaries."""
        logger.info("Starting neighbourhood boundary collection...")

        # Try OpenRegina CKAN for real boundaries first
        boundaries = await self._try_openregina()

        # If that fails, use centroid approximations (which always works)
        if not boundaries:
            logger.info("  Using centroid-based approximate polygons (reliable fallback)")
            boundaries = self._create_from_centroids()

        # Write output
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_neighbourhoods": len(boundaries),
                "city": "Regina",
                "province": "Saskatchewan",
                "source": "centroid_approximation",
            },
            "features": boundaries,
        }

        output_path = self.processed_dir / "neighbourhoods.geojson"
        output_path.write_text(json.dumps(geojson, indent=2))
        logger.info(f"  Written {len(boundaries)} neighbourhood boundaries to {output_path}")

    async def _try_openregina(self) -> list[dict] | None:
        """Quick attempt at OpenRegina CKAN — don't block on failure."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://openregina.ca/api/3/action/package_search",
                    params={"q": "neighbourhood boundary", "rows": 5},
                )
                if response.status_code != 200:
                    return None

                data = response.json()
                results = data.get("result", {}).get("results", [])

                for dataset in results:
                    for resource in dataset.get("resources", []):
                        fmt = resource.get("format", "").lower()
                        if fmt in ("geojson", "json"):
                            url = resource.get("url")
                            if url:
                                resp = await client.get(url, timeout=15.0)
                                if resp.status_code == 200:
                                    geo = resp.json()
                                    features = geo.get("features", [])
                                    if features:
                                        logger.info(f"  Got {len(features)} boundaries from OpenRegina!")
                                        return features
        except Exception as e:
            logger.debug(f"  OpenRegina attempt failed (expected): {e}")

        return None

    def _create_from_centroids(self) -> list[dict]:
        """
        Create approximate neighbourhood polygons from centroids.
        Uses a hexagonal approximation — good enough for display and scoring.
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
