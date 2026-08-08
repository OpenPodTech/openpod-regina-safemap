"""
OpenStreetMap Scraper — Collects schools, parks, transit, and amenities for Regina.

Uses the Overpass API to query OSM data within Regina's bounding box.
No API key needed — Overpass is free and public.

Output:
- data/processed/schools.geojson
- data/processed/parks.geojson
- data/processed/transit_stops.geojson
- data/processed/amenities.geojson
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Regina bounding box (south, west, north, east)
REGINA_BBOX = (50.38, -104.72, 50.50, -104.52)

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class OSMScraper:
    """Collects Points of Interest from OpenStreetMap for Regina."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self):
        """Run all OSM data collection."""
        logger.info("Starting OSM data collection for Regina...")

        await self.collect_schools()
        await self.collect_parks()
        await self.collect_transit_stops()
        await self.collect_amenities()

        logger.info("OSM data collection complete")

    async def collect_schools(self):
        """Fetch all schools in Regina."""
        query = f"""
        [out:json][timeout:60];
        (
          node["amenity"="school"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["amenity"="school"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["amenity"="kindergarten"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
        );
        out center;
        """

        features = await self._run_overpass(query, "schools")
        if features is None:
            return

        geojson_features = []
        for element in features:
            lat, lon = self._get_coords(element)
            if not lat:
                continue

            tags = element.get("tags", {})
            geojson_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "name": tags.get("name", "Unknown School"),
                    "type": tags.get("amenity", "school"),
                    "operator": tags.get("operator", ""),
                    "school_type": self._classify_school(tags),
                    "grades": tags.get("grades", ""),
                    "website": tags.get("website", ""),
                    "phone": tags.get("phone", ""),
                },
            })

        self._write_geojson(geojson_features, "schools.geojson")
        logger.info(f"  Schools: {len(geojson_features)} found")

    async def collect_parks(self):
        """Fetch all parks, playgrounds, and green spaces in Regina."""
        query = f"""
        [out:json][timeout:60];
        (
          node["leisure"="park"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["leisure"="park"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["leisure"="playground"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["leisure"="playground"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["leisure"="sports_centre"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["leisure"="sports_centre"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
        );
        out center;
        """

        features = await self._run_overpass(query, "parks")
        if features is None:
            return

        geojson_features = []
        for element in features:
            lat, lon = self._get_coords(element)
            if not lat:
                continue

            tags = element.get("tags", {})
            geojson_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "name": tags.get("name", "Unnamed Park"),
                    "type": tags.get("leisure", "park"),
                    "sport": tags.get("sport", ""),
                    "surface": tags.get("surface", ""),
                    "lit": tags.get("lit", ""),
                },
            })

        self._write_geojson(geojson_features, "parks.geojson")
        logger.info(f"  Parks & recreation: {len(geojson_features)} found")

    async def collect_transit_stops(self):
        """Fetch all bus stops in Regina."""
        query = f"""
        [out:json][timeout:60];
        (
          node["highway"="bus_stop"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["public_transport"="stop_position"]["bus"="yes"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["public_transport"="platform"]["bus"="yes"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
        );
        out;
        """

        features = await self._run_overpass(query, "transit")
        if features is None:
            return

        geojson_features = []
        for element in features:
            lat, lon = self._get_coords(element)
            if not lat:
                continue

            tags = element.get("tags", {})
            geojson_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "name": tags.get("name", f"Stop {tags.get('ref', 'N/A')}"),
                    "ref": tags.get("ref", ""),
                    "routes": tags.get("route_ref", ""),
                    "shelter": tags.get("shelter", "no"),
                    "bench": tags.get("bench", "no"),
                    "network": tags.get("network", "Regina Transit"),
                },
            })

        self._write_geojson(geojson_features, "transit_stops.geojson")
        logger.info(f"  Transit stops: {len(geojson_features)} found")

    async def collect_amenities(self):
        """Fetch grocery stores, healthcare, libraries, community centres."""
        query = f"""
        [out:json][timeout:60];
        (
          node["shop"="supermarket"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["shop"="convenience"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["amenity"="pharmacy"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["amenity"="hospital"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["amenity"="clinic"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["amenity"="doctors"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["amenity"="library"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          node["amenity"="community_centre"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["shop"="supermarket"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["amenity"="hospital"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["amenity"="library"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
          way["amenity"="community_centre"]({REGINA_BBOX[0]},{REGINA_BBOX[1]},{REGINA_BBOX[2]},{REGINA_BBOX[3]});
        );
        out center;
        """

        features = await self._run_overpass(query, "amenities")
        if features is None:
            return

        geojson_features = []
        for element in features:
            lat, lon = self._get_coords(element)
            if not lat:
                continue

            tags = element.get("tags", {})
            amenity_type = tags.get("amenity") or tags.get("shop") or "unknown"

            geojson_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "name": tags.get("name", "Unnamed"),
                    "type": amenity_type,
                    "category": self._categorize_amenity(amenity_type),
                    "opening_hours": tags.get("opening_hours", ""),
                    "phone": tags.get("phone", ""),
                    "website": tags.get("website", ""),
                },
            })

        self._write_geojson(geojson_features, "amenities.geojson")
        logger.info(f"  Amenities: {len(geojson_features)} found")

    # ─── Helpers ───────────────────────────────────────────────────────────

    async def _run_overpass(self, query: str, name: str) -> list | None:
        """Execute an Overpass API query."""
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(OVERPASS_URL, data={"data": query})
                if response.status_code == 200:
                    data = response.json()
                    elements = data.get("elements", [])

                    # Save raw response
                    raw_path = self.raw_dir / f"osm_{name}.json"
                    raw_path.write_text(json.dumps(data, indent=2))

                    return elements
                else:
                    logger.warning(f"  Overpass query '{name}' returned HTTP {response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"  Overpass query '{name}' failed: {e}")
                return None

    def _get_coords(self, element: dict) -> tuple:
        """Extract lat/lon from an OSM element (node or way with center)."""
        if element.get("type") == "node":
            return element.get("lat"), element.get("lon")
        elif "center" in element:
            return element["center"].get("lat"), element["center"].get("lon")
        return None, None

    def _classify_school(self, tags: dict) -> str:
        """Classify school type from OSM tags."""
        name = tags.get("name", "").lower()
        operator = tags.get("operator", "").lower()

        if "catholic" in name or "catholic" in operator:
            return "catholic"
        elif "french" in name or "francophone" in name or "fransaskois" in operator:
            return "french"
        elif "montessori" in name or "private" in tags.get("school:type", ""):
            return "private"
        elif tags.get("amenity") == "kindergarten":
            return "kindergarten"
        else:
            return "public"

    def _categorize_amenity(self, amenity_type: str) -> str:
        """Group amenity types into categories."""
        categories = {
            "supermarket": "grocery",
            "convenience": "grocery",
            "pharmacy": "healthcare",
            "hospital": "healthcare",
            "clinic": "healthcare",
            "doctors": "healthcare",
            "library": "community",
            "community_centre": "community",
        }
        return categories.get(amenity_type, "other")

    def _write_geojson(self, features: list[dict], filename: str):
        """Write features as a GeoJSON file."""
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_features": len(features),
                "source": "OpenStreetMap via Overpass API",
            },
            "features": features,
        }
        output_path = self.processed_dir / filename
        output_path.write_text(json.dumps(geojson, indent=2))


async def main():
    """Run OSM scraper standalone."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = OSMScraper()
    await scraper.collect_all()


if __name__ == "__main__":
    asyncio.run(main())
