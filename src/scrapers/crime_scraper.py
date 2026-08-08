"""
Crime Data Scraper — Collects crime incident data for Regina.

Data Sources:
1. GitHub: andrewjdyck/regina-crime-data — Historical CSVs by neighbourhood (annual)
2. Regina Police Service Community Crime Map — Recent incidents (ArcGIS/Esri backend)
3. OpenRegina.ca — Any crime-related datasets available

Output: data/processed/crimes.geojson
"""

import asyncio
import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Regina neighbourhood centroids (approximate lat/lon for heatmap placement)
# These are used when crime data is reported by neighbourhood name without coordinates
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
}

# Crime severity weights (for scoring)
CRIME_SEVERITY = {
    "Homicide": 10.0,
    "Robbery": 8.0,
    "Sexual Assault": 9.0,
    "Assault": 7.0,
    "Break and Enter - Residential": 6.0,
    "Break and Enter - Commercial": 5.0,
    "Theft of Motor Vehicle": 5.0,
    "Theft Over $5,000": 4.0,
    "Theft Under $5,000": 2.0,
    "Mischief": 2.0,
    "Drug Offences": 3.0,
    "Fraud": 3.0,
    "Weapons Offences": 7.0,
    "Other Criminal Code": 2.0,
}


class CrimeScraper:
    """Collects and normalizes crime data from multiple sources."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    async def collect_all(self) -> dict:
        """Run all crime data collection methods."""
        logger.info("Starting crime data collection...")

        results = {
            "github_historical": await self.collect_github_historical(),
            "rps_recent": await self.collect_rps_crime_map(),
        }

        # Merge and output final GeoJSON
        all_crimes = []
        for source, crimes in results.items():
            if crimes:
                all_crimes.extend(crimes)
                logger.info(f"  {source}: {len(crimes)} records")

        geojson = self._to_geojson(all_crimes)
        output_path = self.processed_dir / "crimes.geojson"
        output_path.write_text(json.dumps(geojson, indent=2))
        logger.info(f"Written {len(all_crimes)} crime records to {output_path}")

        return results

    async def collect_github_historical(self) -> list[dict]:
        """
        Fetch historical crime CSV data from andrewjdyck/regina-crime-data.
        
        This dataset has crime counts by neighbourhood per year, broken down
        by crime class.
        """
        base_url = "https://raw.githubusercontent.com/andrewjdyck/regina-crime-data/master/data"
        crimes = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try fetching recent years
            for year in range(2019, 2027):
                url = f"{base_url}/{year}.csv"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        logger.info(f"  Fetched {year} crime data from GitHub")
                        year_crimes = self._parse_github_csv(response.text, year)
                        crimes.extend(year_crimes)

                        # Save raw file
                        raw_path = self.raw_dir / f"crime_github_{year}.csv"
                        raw_path.write_text(response.text)
                    else:
                        logger.debug(f"  No data for {year} (HTTP {response.status_code})")
                except Exception as e:
                    logger.warning(f"  Failed to fetch {year}: {e}")

        return crimes

    def _parse_github_csv(self, csv_text: str, year: int) -> list[dict]:
        """Parse GitHub crime CSV into normalized records."""
        crimes = []
        reader = csv.DictReader(io.StringIO(csv_text))

        for row in reader:
            neighbourhood = row.get("Neighbourhood", row.get("neighbourhood", "")).strip()
            if not neighbourhood or neighbourhood.lower() in ("total", "unknown", ""):
                continue

            # Get centroid for this neighbourhood
            centroid = NEIGHBOURHOOD_CENTROIDS.get(neighbourhood)
            if not centroid:
                # Try fuzzy match
                for known, coords in NEIGHBOURHOOD_CENTROIDS.items():
                    if known.lower() in neighbourhood.lower() or neighbourhood.lower() in known.lower():
                        centroid = coords
                        break

            if not centroid:
                centroid = (50.4452, -104.6189)  # Regina city centre fallback

            # Extract crime counts by type
            for field, value in row.items():
                if field.lower() in ("neighbourhood", "total", ""):
                    continue
                try:
                    count = int(value) if value else 0
                except ValueError:
                    continue

                if count > 0:
                    crimes.append({
                        "neighbourhood": neighbourhood,
                        "crime_type": field.strip(),
                        "count": count,
                        "year": year,
                        "lat": centroid[0],
                        "lon": centroid[1],
                        "source": "github_historical",
                        "severity": CRIME_SEVERITY.get(field.strip(), 2.0),
                    })

        return crimes

    async def collect_rps_crime_map(self) -> list[dict]:
        """
        Attempt to collect recent crime data from Regina Police Service.
        
        RPS uses an Esri ArcGIS-based crime map. We attempt to query
        the public feature service endpoint.
        """
        # Known RPS ArcGIS endpoints (these may change — we try multiple)
        endpoints = [
            "https://services.arcgis.com/VsaNWYRmqJifbHjB/arcgis/rest/services/RPS_Community_Crime_Map/FeatureServer/0/query",
            "https://services1.arcgis.com/VsaNWYRmqJifbHjB/arcgis/rest/services/RPS_Crime_Map/FeatureServer/0/query",
        ]

        params = {
            "where": "1=1",
            "outFields": "*",
            "outSR": "4326",
            "f": "json",
            "resultRecordCount": 2000,
        }

        crimes = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for endpoint in endpoints:
                try:
                    response = await client.get(endpoint, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        features = data.get("features", [])
                        if features:
                            logger.info(f"  Fetched {len(features)} incidents from RPS ArcGIS")
                            for feature in features:
                                attrs = feature.get("attributes", {})
                                geom = feature.get("geometry", {})

                                crime = {
                                    "neighbourhood": attrs.get("Neighbourhood", attrs.get("NEIGHBOURHOOD", "Unknown")),
                                    "crime_type": attrs.get("Offence", attrs.get("OFFENCE", attrs.get("Crime_Type", "Unknown"))),
                                    "count": 1,
                                    "year": self._extract_year(attrs),
                                    "month": self._extract_month(attrs),
                                    "lat": geom.get("y", geom.get("latitude", 50.4452)),
                                    "lon": geom.get("x", geom.get("longitude", -104.6189)),
                                    "source": "rps_crime_map",
                                    "severity": 3.0,  # Default, recalculated later
                                }
                                crime["severity"] = CRIME_SEVERITY.get(crime["crime_type"], 3.0)
                                crimes.append(crime)

                            # Save raw response
                            raw_path = self.raw_dir / "crime_rps_arcgis.json"
                            raw_path.write_text(json.dumps(data, indent=2))
                            break  # Got data, no need to try other endpoints

                except Exception as e:
                    logger.warning(f"  RPS endpoint failed ({endpoint}): {e}")

        if not crimes:
            logger.warning("  Could not access RPS crime map API — will use GitHub data only")

        return crimes

    def _extract_year(self, attrs: dict) -> int:
        """Extract year from ArcGIS feature attributes."""
        # Try various field names
        for field in ("Year", "YEAR", "OccurredYear", "Report_Year"):
            if field in attrs and attrs[field]:
                try:
                    return int(attrs[field])
                except (ValueError, TypeError):
                    pass

        # Try date fields
        for field in ("Date", "DATE", "OccurredDate", "Report_Date"):
            if field in attrs and attrs[field]:
                try:
                    # ArcGIS dates are often millisecond timestamps
                    ts = int(attrs[field]) / 1000
                    return datetime.fromtimestamp(ts).year
                except (ValueError, TypeError, OSError):
                    pass

        return datetime.now().year

    def _extract_month(self, attrs: dict) -> Optional[int]:
        """Extract month from ArcGIS feature attributes."""
        for field in ("Month", "MONTH", "OccurredMonth"):
            if field in attrs and attrs[field]:
                try:
                    return int(attrs[field])
                except (ValueError, TypeError):
                    pass
        return None

    def _to_geojson(self, crimes: list[dict]) -> dict:
        """Convert crime records to GeoJSON FeatureCollection."""
        features = []

        for crime in crimes:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [crime["lon"], crime["lat"]],
                },
                "properties": {
                    "neighbourhood": crime["neighbourhood"],
                    "crime_type": crime["crime_type"],
                    "count": crime["count"],
                    "year": crime["year"],
                    "severity": crime["severity"],
                    "source": crime["source"],
                },
            }
            if "month" in crime and crime.get("month"):
                feature["properties"]["month"] = crime["month"]

            features.append(feature)

        return {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_records": len(features),
                "sources": list(set(c["source"] for c in crimes)),
            },
            "features": features,
        }


async def main():
    """Run crime scraper standalone."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    scraper = CrimeScraper()
    await scraper.collect_all()


if __name__ == "__main__":
    asyncio.run(main())
