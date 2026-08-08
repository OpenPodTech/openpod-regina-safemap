"""
Crime Data Scraper — Collects crime incident data for Regina.

Data Source:
  GitHub: andrewjdyck/regina-crime-data — Historical CSVs by neighbourhood (2007-2018)
  URL pattern: https://raw.githubusercontent.com/andrewjdyck/regina-crime-data/master/data/crime_report_YYYY.csv
  Combined file: https://raw.githubusercontent.com/andrewjdyck/regina-crime-data/master/data/regina_crime_reports.csv

CSV format: "crime","neighbourhood","incidents","year"

Output: data/processed/crimes.geojson
"""

import asyncio
import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Regina neighbourhood centroids (approximate lat/lon for heatmap placement)
NEIGHBOURHOOD_CENTROIDS = {
    "Al Ritchie": (50.4372, -104.6097),
    "Albert Park": (50.4180, -104.6360),
    "Arcola East": (50.4220, -104.5800),
    "Argyle Park": (50.4350, -104.5900),
    "Boothill": (50.4410, -104.5780),
    "Broder Annex": (50.4310, -104.5950),
    "Cathedral": (50.4530, -104.6250),
    "Centre Square": (50.4480, -104.6050),
    "Churchill Downs": (50.4000, -104.6000),
    "Coronation Park": (50.4600, -104.5850),
    "Core": (50.4500, -104.6100),
    "Core Group": (50.4500, -104.6100),
    "Crescents": (50.4430, -104.6200),
    "Dewdney East": (50.4560, -104.5900),
    "Dieppe": (50.4770, -104.6100),
    "Douglas Park": (50.4250, -104.6400),
    "Downtown": (50.4490, -104.6120),
    "Eastview": (50.4540, -104.5680),
    "Elphinstone": (50.4530, -104.6350),
    "Gardiner Park": (50.4100, -104.5700),
    "General Hospital": (50.4430, -104.5850),
    "Gladmer Park": (50.4650, -104.6200),
    "Glen Elm": (50.4380, -104.5750),
    "Glencairn": (50.4730, -104.6350),
    "Harbour Landing": (50.4050, -104.6500),
    "Hawkstone": (50.3950, -104.6600),
    "Heritage": (50.4210, -104.6100),
    "Hillsdale": (50.4750, -104.5900),
    "Hollywood Hill": (50.4270, -104.5700),
    "Kensington": (50.4100, -104.6200),
    "Lakeridge": (50.4080, -104.5900),
    "Lakeview": (50.4350, -104.6470),
    "Lakewood": (50.4170, -104.5600),
    "Market Square": (50.4490, -104.6050),
    "McCarthy Park": (50.4890, -104.5900),
    "McNab": (50.4600, -104.5700),
    "Mount Royal": (50.4300, -104.6250),
    "Normandy Heights": (50.4800, -104.6000),
    "North Central": (50.4620, -104.6200),
    "Normanview": (50.4700, -104.6600),
    "Normanview West": (50.4700, -104.6750),
    "Oakwood": (50.4100, -104.5500),
    "Old Lakeview": (50.4300, -104.6470),
    "Parliament Place": (50.4450, -104.6400),
    "Parkdale": (50.4530, -104.5950),
    "Prairie View": (50.4100, -104.6700),
    "Regent Park": (50.4460, -104.5700),
    "Richmond Place": (50.4500, -104.5600),
    "Rosemont": (50.4680, -104.6350),
    "Ross Industrial": (50.4590, -104.5500),
    "Sherwood Estates": (50.4850, -104.6200),
    "Skyview": (50.4150, -104.6400),
    "South Lakeview": (50.4280, -104.6470),
    "Southeast Industrial": (50.4100, -104.5400),
    "Tuxedo Park": (50.4450, -104.5850),
    "Twin Lakes": (50.4050, -104.6200),
    "University Park": (50.4170, -104.5870),
    "Uplands": (50.4700, -104.5700),
    "Walsh Acres": (50.4800, -104.6500),
    "Washington Park": (50.4350, -104.6150),
    "Wascana Centre": (50.4300, -104.6150),
    "Wascana View": (50.4070, -104.5500),
    "Westhill": (50.4450, -104.6500),
    "Whitmore Park": (50.4200, -104.6500),
    "Windsor Park": (50.4350, -104.5600),
    # Common alternate names / extras found in the CSV data
    "Transitional": (50.4500, -104.6050),
    "Walsh Acres Industrial": (50.4820, -104.6550),
    "Warehouse District": (50.4520, -104.6050),
    "Rochdale": (50.4850, -104.6400),
    "Wood Meadows": (50.3980, -104.6400),
    "The Creeks": (50.3960, -104.6300),
    "Greens on Gardiner": (50.4050, -104.5650),
}

# Crime severity weights — mapped to the crime names used in the actual CSV
CRIME_SEVERITY = {
    # HIGH severity — violent crimes
    "Assault": 7.0,
    "Attempt Murder": 10.0,
    "Sexual Assault": 9.0,
    "Homicide": 10.0,
    "Robbery": 8.0,
    # MEDIUM severity — property crime affecting individuals
    "B&E (Residence)": 6.0,
    "B&E (Other)": 5.0,
    "Theft of Motor Vehicle": 5.0,
    "Theft Over": 4.0,
    # LOW severity — nuisance / minor
    "Mischief": 2.0,
    "Other Theft Under": 2.0,
    "Shoplift": 1.5,
    "Other Crime": 2.0,
}

# Default severity for crime types not in the map
DEFAULT_SEVERITY = 3.0


def get_severity(crime_type: str) -> float:
    """Look up severity, with fuzzy matching for partial crime type names."""
    if crime_type in CRIME_SEVERITY:
        return CRIME_SEVERITY[crime_type]
    # Fuzzy match
    crime_lower = crime_type.lower()
    for known, weight in CRIME_SEVERITY.items():
        if known.lower() in crime_lower or crime_lower in known.lower():
            return weight
    return DEFAULT_SEVERITY


def get_centroid(neighbourhood: str) -> tuple[float, float]:
    """Look up centroid for neighbourhood, with fuzzy matching."""
    if neighbourhood in NEIGHBOURHOOD_CENTROIDS:
        return NEIGHBOURHOOD_CENTROIDS[neighbourhood]
    # Try case-insensitive / partial match
    neighbourhood_lower = neighbourhood.lower().strip()
    for known, coords in NEIGHBOURHOOD_CENTROIDS.items():
        if known.lower() == neighbourhood_lower:
            return coords
    for known, coords in NEIGHBOURHOOD_CENTROIDS.items():
        if known.lower() in neighbourhood_lower or neighbourhood_lower in known.lower():
            return coords
    # Fallback to city centre
    return (50.4452, -104.6189)


class CrimeScraper:
    """Collects and normalizes crime data from GitHub CSV source."""

    BASE_URL = "https://raw.githubusercontent.com/andrewjdyck/regina-crime-data/master/data"
    YEARS = range(2007, 2019)  # 2007 through 2018

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self) -> dict:
        """Run all crime data collection methods."""
        logger.info("Starting crime data collection...")

        all_crimes = []

        # Try combined file first
        combined = await self._fetch_combined()
        if combined:
            all_crimes.extend(combined)
            logger.info(f"  Combined file: {len(combined)} records")
        else:
            # Fetch individual year files
            yearly = await self._fetch_yearly()
            all_crimes.extend(yearly)
            logger.info(f"  Yearly files: {len(yearly)} records")

        if not all_crimes:
            logger.error("  NO CRIME DATA COLLECTED — all sources failed!")
            # Write empty geojson so downstream doesn't crash
            self._write_empty_geojson()
            return {"total": 0}

        # Compute neighbourhood aggregates and trends
        neighbourhood_stats = self._compute_neighbourhood_stats(all_crimes)

        # Build heatmap-ready GeoJSON (one point per neighbourhood per crime type per year)
        geojson = self._to_geojson(all_crimes, neighbourhood_stats)
        output_path = self.processed_dir / "crimes.geojson"
        output_path.write_text(json.dumps(geojson, indent=2))
        logger.info(f"  Written {len(geojson['features'])} crime features to {output_path}")

        # Also write neighbourhood crime stats summary
        stats_path = self.processed_dir / "crime_stats.json"
        stats_path.write_text(json.dumps(neighbourhood_stats, indent=2))
        logger.info(f"  Written neighbourhood crime stats to {stats_path}")

        return {"total": len(all_crimes), "neighbourhoods": len(neighbourhood_stats)}

    async def _fetch_combined(self) -> list[dict]:
        """Try fetching the combined regina_crime_reports.csv."""
        url = f"{self.BASE_URL}/regina_crime_reports.csv"
        crimes = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    logger.info(f"  Fetched combined crime data from {url}")
                    crimes = self._parse_csv(response.text)
                    # Save raw
                    raw_path = self.raw_dir / "regina_crime_reports.csv"
                    raw_path.write_text(response.text)
                else:
                    logger.info(f"  Combined file not available (HTTP {response.status_code})")
            except Exception as e:
                logger.warning(f"  Failed to fetch combined file: {e}")

        return crimes

    async def _fetch_yearly(self) -> list[dict]:
        """Fetch individual year CSV files (crime_report_YYYY.csv)."""
        crimes = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for year in self.YEARS:
                url = f"{self.BASE_URL}/crime_report_{year}.csv"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"  Fetched {year} crime data")
                        year_crimes = self._parse_csv(response.text)
                        crimes.extend(year_crimes)
                        # Save raw
                        raw_path = self.raw_dir / f"crime_report_{year}.csv"
                        raw_path.write_text(response.text)
                    else:
                        logger.debug(f"  No data for {year} (HTTP {response.status_code})")
                except Exception as e:
                    logger.warning(f"  Failed to fetch {year}: {e}")

        return crimes

    def _parse_csv(self, csv_text: str) -> list[dict]:
        """
        Parse the actual CSV format:
        "crime","neighbourhood","incidents","year"
        "Assault","North Central",457,2018
        """
        crimes = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            crime_type = row.get("crime", "").strip()
            neighbourhood = row.get("neighbourhood", "").strip()
            year_str = row.get("year", "").strip()
            incidents_str = row.get("incidents", "0").strip()

            # Skip empty/total rows
            if not neighbourhood or not crime_type:
                continue
            if neighbourhood.lower() in ("total", "unknown", "", "all"):
                continue
            if crime_type.lower() in ("total", ""):
                continue

            try:
                incidents = int(incidents_str)
            except (ValueError, TypeError):
                try:
                    incidents = int(float(incidents_str))
                except (ValueError, TypeError):
                    continue

            try:
                year = int(year_str)
            except (ValueError, TypeError):
                continue

            if incidents <= 0:
                continue

            centroid = get_centroid(neighbourhood)
            severity = get_severity(crime_type)

            crimes.append({
                "neighbourhood": neighbourhood,
                "crime_type": crime_type,
                "incidents": incidents,
                "year": year,
                "lat": centroid[0],
                "lon": centroid[1],
                "severity": severity,
            })

        return crimes

    def _compute_neighbourhood_stats(self, crimes: list[dict]) -> dict:
        """
        Compute per-neighbourhood stats:
        - Total incidents (all years)
        - Latest year total
        - Previous year total
        - Year-over-year trend
        - Crime breakdown by type
        - Weighted severity score
        """
        from collections import defaultdict

        # Group by neighbourhood
        by_hood = defaultdict(list)
        for crime in crimes:
            by_hood[crime["neighbourhood"]].append(crime)

        stats = {}
        latest_year = max(c["year"] for c in crimes)
        prev_year = latest_year - 1

        for hood, records in by_hood.items():
            total_incidents = sum(r["incidents"] for r in records)
            latest_incidents = sum(r["incidents"] for r in records if r["year"] == latest_year)
            prev_incidents = sum(r["incidents"] for r in records if r["year"] == prev_year)

            # Year-over-year trend
            if prev_incidents > 0:
                yoy_change = ((latest_incidents - prev_incidents) / prev_incidents) * 100
            else:
                yoy_change = 0.0

            # Weighted severity (higher = more dangerous)
            weighted_score = sum(r["incidents"] * r["severity"] for r in records if r["year"] == latest_year)

            # Crime breakdown for latest year
            breakdown = defaultdict(int)
            for r in records:
                if r["year"] == latest_year:
                    breakdown[r["crime_type"]] += r["incidents"]

            stats[hood] = {
                "total_all_years": total_incidents,
                "latest_year": latest_year,
                "latest_incidents": latest_incidents,
                "prev_incidents": prev_incidents,
                "yoy_change_pct": round(yoy_change, 1),
                "yoy_trend": "increasing" if yoy_change > 5 else ("decreasing" if yoy_change < -5 else "stable"),
                "weighted_severity_score": round(weighted_score, 1),
                "crime_breakdown": dict(breakdown),
                "centroid": list(get_centroid(hood)),
            }

        return stats

    def _to_geojson(self, crimes: list[dict], neighbourhood_stats: dict) -> dict:
        """
        Convert crime records to GeoJSON for the heatmap.
        
        Strategy: Create multiple points per neighbourhood proportional to crime count,
        with slight random offset to create heatmap density. High-crime areas get more
        points = hotter on heatmap.
        """
        import random
        random.seed(42)  # Reproducible jitter

        features = []
        latest_year = max(c["year"] for c in crimes)

        # For the heatmap, we want to emphasize recent data
        # Use latest 3 years of data, weighted toward most recent
        recent_years = {latest_year: 1.0, latest_year - 1: 0.6, latest_year - 2: 0.3}

        for crime in crimes:
            if crime["year"] not in recent_years:
                continue

            year_weight = recent_years[crime["year"]]
            base_lat = crime["lat"]
            base_lon = crime["lon"]
            severity = crime["severity"]
            incidents = crime["incidents"]

            # Calculate intensity for this record
            # Scale: severity * year_weight, normalized
            intensity = min((severity * year_weight * incidents) / 500.0, 1.0)

            # For high-incident records, create multiple points with jitter
            # This makes high-crime areas glow hotter on the heatmap
            num_points = max(1, min(incidents // 10, 20))  # Cap at 20 points per record

            for _ in range(num_points):
                # Add jitter within ~300m radius to spread across neighbourhood
                jitter_lat = random.gauss(0, 0.002)
                jitter_lon = random.gauss(0, 0.003)

                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            round(base_lon + jitter_lon, 6),
                            round(base_lat + jitter_lat, 6),
                        ],
                    },
                    "properties": {
                        "neighbourhood": crime["neighbourhood"],
                        "crime_type": crime["crime_type"],
                        "count": incidents,
                        "year": crime["year"],
                        "severity": severity,
                        "intensity": round(intensity, 3),
                        "source": "github_historical",
                    },
                }
                features.append(feature)

        # Sort by intensity so high-crime areas render on top
        features.sort(key=lambda f: f["properties"]["intensity"])

        return {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_records": len(features),
                "total_raw_records": len(crimes),
                "years_included": sorted(recent_years.keys()),
                "sources": ["andrewjdyck/regina-crime-data"],
                "neighbourhood_count": len(neighbourhood_stats),
                "highest_crime": max(neighbourhood_stats.items(), key=lambda x: x[1]["latest_incidents"])[0] if neighbourhood_stats else None,
                "lowest_crime": min(neighbourhood_stats.items(), key=lambda x: x[1]["latest_incidents"])[0] if neighbourhood_stats else None,
            },
            "features": features,
        }

    def _write_empty_geojson(self):
        """Write an empty GeoJSON as fallback."""
        empty = {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_records": 0,
                "sources": [],
                "error": "No crime data could be collected",
            },
            "features": [],
        }
        output_path = self.processed_dir / "crimes.geojson"
        output_path.write_text(json.dumps(empty, indent=2))


async def main():
    """Run crime scraper standalone."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = CrimeScraper()
    await scraper.collect_all()


if __name__ == "__main__":
    asyncio.run(main())
