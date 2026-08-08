"""
Builds historical trend data by fetching crime_report_YYYY.csv files from GitHub.
Source: https://github.com/andrewjdyck/regina-crime-data/tree/master/data
Combines historical (2007-2018) with live crime_stats.json for a complete picture.
"""
import asyncio
import csv
import io
import json
import logging
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

GITHUB_BASE = "https://raw.githubusercontent.com/andrewjdyck/regina-crime-data/master/data"
YEARS = range(2007, 2019)  # 2007-2018 available

# Project root (two levels up from src/scrapers/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def fetch_year(client: httpx.AsyncClient, year: int) -> list[dict]:
    """Fetch and parse a single year's CSV from GitHub."""
    url = f"{GITHUB_BASE}/crime_report_{year}.csv"
    try:
        r = await client.get(url)
        if r.status_code == 200:
            reader = csv.DictReader(io.StringIO(r.text))
            rows = list(reader)
            logger.info(f"  {year}: {len(rows)} rows fetched")
            return rows
        else:
            logger.warning(f"  {year}: HTTP {r.status_code}")
            return []
    except Exception as e:
        logger.error(f"  {year}: Error — {e}")
        return []


async def build_trends():
    """Fetch all historical CSVs and build trends.json."""
    logger.info("Building historical trends...")

    # {neighbourhood: {year: total_incidents}}
    yearly_data = defaultdict(lambda: defaultdict(int))
    # {neighbourhood: {year: {crime_type: count}}}
    yearly_breakdown = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [fetch_year(client, year) for year in YEARS]
        results = await asyncio.gather(*tasks)

        for year, rows in zip(YEARS, results):
            for row in rows:
                hood = row.get("neighbourhood", "").strip()
                crime = row.get("crime", "").strip()
                incidents_str = row.get("incidents", "0").strip() or "0"

                try:
                    incidents = int(incidents_str)
                except ValueError:
                    continue

                # Skip aggregation rows
                if not hood or hood.lower() in ("total", ""):
                    continue
                if crime.lower() == "total":
                    continue
                if incidents <= 0:
                    continue

                yearly_data[hood][year] += incidents
                yearly_breakdown[hood][year][crime] += incidents

    logger.info(f"Historical data: {len(yearly_data)} neighbourhoods across {len(list(YEARS))} years")

    # Load current live stats
    stats_path = PROJECT_ROOT / "data" / "processed" / "crime_stats.json"
    if stats_path.exists():
        live_stats = json.loads(stats_path.read_text(encoding="utf-8"))
        for hood, data in live_stats.items():
            total = data.get("total_incidents", 0)
            if total > 0:
                yearly_data[hood][2026] = total
                breakdown = data.get("crime_breakdown", {})
                for crime, count in breakdown.items():
                    yearly_breakdown[hood][2026][crime] += count
        logger.info(f"Added 2026 live data for {len(live_stats)} neighbourhoods")

    # Build per-neighbourhood trend analysis
    trends = {}
    city_yearly_totals = defaultdict(int)

    for hood, years in yearly_data.items():
        sorted_years = dict(sorted(years.items()))
        totals = list(sorted_years.values())
        year_keys = list(sorted_years.keys())

        if not totals:
            continue

        peak_idx = totals.index(max(totals))
        low_idx = totals.index(min(totals))

        # Calculate overall trend (2007 to 2018)
        if 2018 in sorted_years and 2007 in sorted_years and sorted_years[2007] > 0:
            change = ((sorted_years[2018] - sorted_years[2007]) / sorted_years[2007]) * 100
        else:
            change = 0.0

        # Find top crime type across all years for this neighbourhood
        all_crimes = defaultdict(int)
        for yr_crimes in yearly_breakdown[hood].values():
            for crime, count in yr_crimes.items():
                all_crimes[crime] += count
        top_crime = max(all_crimes, key=all_crimes.get) if all_crimes else "Unknown"

        trends[hood] = {
            "yearly_totals": {str(k): v for k, v in sorted_years.items()},
            "peak_year": int(year_keys[peak_idx]),
            "peak_total": totals[peak_idx],
            "lowest_year": int(year_keys[low_idx]),
            "lowest_total": totals[low_idx],
            "overall_change_pct": round(change, 1),
            "overall_trend": "improving" if change < -5 else ("worsening" if change > 5 else "stable"),
            "dominant_crime_type": top_crime,
            "total_all_years": sum(totals),
        }

        # Accumulate city totals
        for yr, count in sorted_years.items():
            city_yearly_totals[yr] += count

    # City-wide summary
    city_sorted = dict(sorted(city_yearly_totals.items()))
    city_totals_list = list(city_sorted.values())
    city_years_list = list(city_sorted.keys())

    if city_totals_list:
        city_peak_idx = city_totals_list.index(max(city_totals_list))
        city_low_idx = city_totals_list.index(min(city_totals_list))
    else:
        city_peak_idx = city_low_idx = 0

    output = {
        "metadata": {
            "years_available": sorted(set(y for years in yearly_data.values() for y in years.keys())),
            "total_neighbourhoods": len(trends),
            "generated": datetime.now().isoformat(),
            "data_sources": [
                "github.com/andrewjdyck/regina-crime-data (2007-2018)",
                "Regina Police Service Open Data (2026)"
            ],
            "note": "2019-2025 data gap — FOIA request pending to Regina Police Service"
        },
        "city_summary": {
            "yearly_totals": {str(k): v for k, v in city_sorted.items()},
            "peak_year": int(city_years_list[city_peak_idx]) if city_years_list else None,
            "peak_total": city_totals_list[city_peak_idx] if city_totals_list else 0,
            "lowest_year": int(city_years_list[city_low_idx]) if city_years_list else None,
            "lowest_total": city_totals_list[city_low_idx] if city_totals_list else 0,
        },
        "neighbourhoods": trends,
    }

    output_path = PROJECT_ROOT / "data" / "processed" / "trends.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info(f"Wrote trends.json: {len(trends)} neighbourhoods, {len(city_sorted)} years")

    # Also copy to frontend for static serving
    frontend_data_path = PROJECT_ROOT / "frontend" / "data" / "processed" / "trends.json"
    frontend_data_path.parent.mkdir(parents=True, exist_ok=True)
    frontend_data_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info(f"Copied to frontend/data/processed/trends.json")


if __name__ == "__main__":
    asyncio.run(build_trends())
