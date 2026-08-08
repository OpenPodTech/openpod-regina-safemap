"""
Crime Data Scraper — Collects LIVE crime incident data from Regina Police Service.

Data Source (PRIMARY — LIVE, updated daily):
  Regina Police Service ArcGIS Feature Service
  URL: https://services6.arcgis.com/EXgfJNbcrqacNMPa/arcgis/rest/services/SecureCommunityCrimeMap/FeatureServer/4/query
  ~3,000+ records, paginated at 2000/request

Data Source (SECONDARY — historical baseline):
  GitHub: andrewjdyck/regina-crime-data — Historical CSVs (2007-2018)
  Used only for long-term trend comparison

Output: data/processed/crimes.geojson, data/processed/crime_stats.json
"""

import asyncio
import csv
import io
import json
import logging
import random
from datetime import datetime
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Live API endpoint — Regina Police Service ArcGIS Feature Service
CRIME_API_URL = (
    "https://services6.arcgis.com/EXgfJNbcrqacNMPa/arcgis/rest/services/"
    "SecureCommunityCrimeMap/FeatureServer/4/query"
)

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
    "Rosemont North": (50.4700, -104.6380),
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
    # Common alternate names / extras
    "Transitional": (50.4500, -104.6050),
    "Walsh Acres Industrial": (50.4820, -104.6550),
    "Warehouse District": (50.4520, -104.6050),
    "Rochdale": (50.4850, -104.6400),
    "Wood Meadows": (50.3980, -104.6400),
    "The Creeks": (50.3960, -104.6300),
    "Greens on Gardiner": (50.4050, -104.5650),
}

# Crime severity weights — mapped to live API CrimeTypes values
CRIME_SEVERITY = {
    # HIGH severity — crimes against the person
    "Assault": 7.0,
    "Sexual Assault": 9.0,
    "Robbery": 8.0,
    "Homicide": 10.0,
    "Attempt Murder": 10.0,
    # MEDIUM severity — property crimes
    "Break & Enter": 6.0,
    "B&E (Residence)": 6.0,
    "B&E (Other)": 5.0,
    "Theft": 3.0,
    "Theft of Motor Vehicle": 5.0,
    "Theft Over": 4.0,
    "Other Theft Under": 2.0,
    # LOW severity — nuisance
    "Mischief": 2.0,
    "Shoplift": 1.5,
    "Other Crime": 2.0,
}

# Severity by crime group (fallback)
CRIME_GROUP_SEVERITY = {
    "Crime Against the Person": 7.0,
    "Crime Against Property": 4.0,
}

DEFAULT_SEVERITY = 3.0


def get_severity(crime_type: str, crime_group: str = "") -> float:
    """Look up severity, with fuzzy matching for partial crime type names."""
    if crime_type in CRIME_SEVERITY:
        return CRIME_SEVERITY[crime_type]
    # Fuzzy match on crime type
    crime_lower = crime_type.lower()
    for known, weight in CRIME_SEVERITY.items():
        if known.lower() in crime_lower or crime_lower in known.lower():
            return weight
    # Fallback to crime group
    if crime_group in CRIME_GROUP_SEVERITY:
        return CRIME_GROUP_SEVERITY[crime_group]
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
    """Collects live crime data from Regina Police Service ArcGIS API."""

    # Historical data (secondary source for trend comparison)
    GITHUB_URL = "https://raw.githubusercontent.com/andrewjdyck/regina-crime-data/master/data/regina_crime_reports.csv"

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self) -> dict:
        """Run all crime data collection — live API is primary source."""
        logger.info("Starting crime data collection (LIVE API)...")

        # PRIMARY: Fetch live data from Regina Police ArcGIS
        live_records = await self.collect_live_data()
        logger.info(f"  Live API: {len(live_records)} records")

        if not live_records:
            logger.error("  LIVE API FAILED — no crime data collected!")
            self._write_empty_geojson()
            return {"total": 0}

        # Save raw live data
        raw_path = self.raw_dir / "live_crime_data.json"
        raw_path.write_text(json.dumps(live_records, indent=2))

        # Compute neighbourhood stats from live data
        neighbourhood_stats = self._compute_live_stats(live_records)

        # Build heatmap GeoJSON
        geojson = self._to_geojson(live_records, neighbourhood_stats)
        output_path = self.processed_dir / "crimes.geojson"
        output_path.write_text(json.dumps(geojson, indent=2))
        logger.info(f"  Written {len(geojson['features'])} crime features to {output_path}")

        # Write neighbourhood crime stats
        stats_path = self.processed_dir / "crime_stats.json"
        stats_path.write_text(json.dumps(neighbourhood_stats, indent=2))
        logger.info(f"  Written neighbourhood crime stats to {stats_path}")

        return {"total": len(live_records), "neighbourhoods": len(neighbourhood_stats)}

    async def collect_live_data(self) -> list[dict]:
        """Fetch live crime data from Regina Police Service ArcGIS Feature Service."""
        all_records = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Paginate — max 2000 records per request, total ~3000+
            for offset in range(0, 10000, 2000):
                params = {
                    "where": "1=1",
                    "outFields": "*",
                    "resultRecordCount": 2000,
                    "resultOffset": offset,
                    "f": "json",
                }
                try:
                    response = await client.get(CRIME_API_URL, params=params)
                    if response.status_code != 200:
                        logger.warning(f"  API returned HTTP {response.status_code} at offset {offset}")
                        break

                    data = response.json()
                    features = data.get("features", [])
                    if not features:
                        break

                    for feature in features:
                        attrs = feature.get("attributes", {})
                        record = {
                            "location": attrs.get("Location", ""),
                            "crime_group": attrs.get("CrimeGroup", ""),
                            "crime_type": attrs.get("CrimeTypes", ""),
                            "neighbourhood": attrs.get("Subdivision", "Unknown"),
                            "ward": attrs.get("Wards", ""),
                            "report_date": attrs.get("ReportDate", ""),
                            "report_date_epoch": attrs.get("Report_Date"),
                            "time_frame": attrs.get("TimeFrame", ""),
                            "last_updated": attrs.get("LastUpdateTime", ""),
                        }
                        all_records.append(record)

                    logger.info(f"  Fetched {len(features)} records at offset {offset}")

                    # If we got fewer than 2000, we've reached the end
                    if len(features) < 2000:
                        break

                except httpx.TimeoutException:
                    logger.warning(f"  Timeout at offset {offset}, retrying...")
                    await asyncio.sleep(2)
                    try:
                        response = await client.get(CRIME_API_URL, params=params)
                        if response.status_code == 200:
                            data = response.json()
                            features = data.get("features", [])
                            for feature in features:
                                attrs = feature.get("attributes", {})
                                all_records.append({
                                    "location": attrs.get("Location", ""),
                                    "crime_group": attrs.get("CrimeGroup", ""),
                                    "crime_type": attrs.get("CrimeTypes", ""),
                                    "neighbourhood": attrs.get("Subdivision", "Unknown"),
                                    "ward": attrs.get("Wards", ""),
                                    "report_date": attrs.get("ReportDate", ""),
                                    "report_date_epoch": attrs.get("Report_Date"),
                                    "time_frame": attrs.get("TimeFrame", ""),
                                    "last_updated": attrs.get("LastUpdateTime", ""),
                                })
                    except Exception as e:
                        logger.error(f"  Retry failed at offset {offset}: {e}")
                        break
                except Exception as e:
                    logger.error(f"  Error fetching at offset {offset}: {e}")
                    break

        return all_records

    def _compute_live_stats(self, records: list[dict]) -> dict:
        """
        Compute per-neighbourhood stats from live data.

        Since we have 30-90 days of rolling data (not year-over-year),
        stats focus on current incident counts, severity, and type breakdown.
        """
        from collections import defaultdict

        # Group by neighbourhood
        by_hood = defaultdict(list)
        for record in records:
            hood = record.get("neighbourhood", "Unknown")
            if hood and hood != "Unknown":
                by_hood[hood].append(record)

        stats = {}

        # Get the date range from the data
        all_dates = [r["report_date"] for r in records if r.get("report_date")]
        if all_dates:
            latest_date = max(all_dates)
            earliest_date = min(all_dates)
        else:
            latest_date = datetime.now().strftime("%Y-%m-%d")
            earliest_date = latest_date

        for hood, hood_records in by_hood.items():
            total_incidents = len(hood_records)

            # Crime type breakdown
            breakdown = defaultdict(int)
            for r in hood_records:
                ctype = r.get("crime_type", "Other")
                if ctype:
                    breakdown[ctype] += 1

            # Crime group breakdown
            group_breakdown = defaultdict(int)
            for r in hood_records:
                group = r.get("crime_group", "")
                if group:
                    group_breakdown[group] += 1

            # Weighted severity score
            weighted_severity = 0.0
            for r in hood_records:
                weighted_severity += get_severity(
                    r.get("crime_type", ""),
                    r.get("crime_group", ""),
                )

            # Person vs property ratio
            person_crimes = group_breakdown.get("Crime Against the Person", 0)
            property_crimes = group_breakdown.get("Crime Against Property", 0)

            stats[hood] = {
                "total_incidents": total_incidents,
                "latest_incidents": total_incidents,  # For scoring compatibility
                "weighted_severity_score": round(weighted_severity, 1),
                "crime_breakdown": dict(breakdown),
                "crime_group_breakdown": dict(group_breakdown),
                "person_crimes": person_crimes,
                "property_crimes": property_crimes,
                "data_period": f"{earliest_date} to {latest_date}",
                "last_updated": latest_date,
                "centroid": list(get_centroid(hood)),
                # For scoring compatibility (no YOY with live rolling data)
                "yoy_change_pct": 0.0,
                "yoy_trend": "current",
            }

        return stats

    def _to_geojson(self, records: list[dict], neighbourhood_stats: dict) -> dict:
        """
        Convert live crime records to GeoJSON for heatmap.

        Strategy: Since the API returns block-level location text (no coordinates),
        we place heatmap points at neighbourhood centroids with jitter proportional
        to crime count. More incidents = more points = hotter on heatmap.
        """
        random.seed(42)  # Reproducible jitter

        features = []

        # Group records by neighbourhood for efficient point generation
        from collections import defaultdict
        by_hood = defaultdict(list)
        for record in records:
            hood = record.get("neighbourhood", "Unknown")
            if hood and hood != "Unknown":
                by_hood[hood].append(record)

        for hood, hood_records in by_hood.items():
            centroid = get_centroid(hood)
            base_lat = centroid[0]
            base_lon = centroid[1]

            for record in hood_records:
                crime_type = record.get("crime_type", "Other")
                crime_group = record.get("crime_group", "")
                severity = get_severity(crime_type, crime_group)

                # Intensity: normalized severity (0-1)
                intensity = min(severity / 10.0, 1.0)

                # Add jitter within ~400m radius to spread across neighbourhood
                jitter_lat = random.gauss(0, 0.0025)
                jitter_lon = random.gauss(0, 0.0035)

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
                        "neighbourhood": hood,
                        "crime_type": crime_type,
                        "crime_group": crime_group,
                        "report_date": record.get("report_date", ""),
                        "location": record.get("location", ""),
                        "severity": severity,
                        "intensity": round(intensity, 3),
                        "source": "rps_live",
                    },
                }
                features.append(feature)

        # Sort by intensity so high-severity renders on top
        features.sort(key=lambda f: f["properties"]["intensity"])

        # Determine last update time
        last_updated_values = [r.get("last_updated", "") for r in records if r.get("last_updated")]
        last_updated = max(last_updated_values) if last_updated_values else datetime.now().isoformat()

        return {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "last_updated": last_updated,
                "total_records": len(features),
                "total_raw_records": len(records),
                "source": "Regina Police Service — Secure Community Crime Map",
                "source_url": CRIME_API_URL,
                "update_frequency": "Daily",
                "neighbourhood_count": len(neighbourhood_stats),
                "highest_crime": (
                    max(neighbourhood_stats.items(), key=lambda x: x[1]["total_incidents"])[0]
                    if neighbourhood_stats else None
                ),
                "lowest_crime": (
                    min(neighbourhood_stats.items(), key=lambda x: x[1]["total_incidents"])[0]
                    if neighbourhood_stats else None
                ),
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
                "source": "Regina Police Service — Secure Community Crime Map",
                "error": "Live API unavailable — no crime data collected",
            },
            "features": [],
        }
        output_path = self.processed_dir / "crimes.geojson"
        output_path.write_text(json.dumps(empty, indent=2))


async def main():
    """Run crime scraper standalone."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = CrimeScraper()
    result = await scraper.collect_all()
    print(f"\nDone: {result}")


if __name__ == "__main__":
    asyncio.run(main())
