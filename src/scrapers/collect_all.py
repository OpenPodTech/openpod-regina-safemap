"""
Collect All Data — Master script to run all scrapers.

Usage:
    python -m src.scrapers.collect_all

This collects:
- Crime data (RPS + GitHub historical)
- Neighbourhood boundaries (OpenRegina / GIS / OSM)
- Schools, parks, transit, amenities (OSM)
"""

import asyncio
import logging
import time

from .crime_scraper import CrimeScraper
from .neighbourhood_scraper import NeighbourhoodScraper
from .osm_scraper import OSMScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("safemap.collector")


async def collect_all():
    """Run all data scrapers in sequence."""
    start = time.time()

    logger.info("=" * 60)
    logger.info("  REGINA SAFEMAP — Data Collection")
    logger.info("  OpenPod Civic Tech")
    logger.info("=" * 60)

    # 1. Neighbourhood boundaries (needed first for scoring)
    logger.info("\n[1/3] Collecting neighbourhood boundaries...")
    neighbourhood_scraper = NeighbourhoodScraper()
    await neighbourhood_scraper.collect_all()

    # 2. Crime data
    logger.info("\n[2/3] Collecting crime data...")
    crime_scraper = CrimeScraper()
    await crime_scraper.collect_all()

    # 3. OSM amenities (schools, parks, transit, shops)
    logger.info("\n[3/3] Collecting OSM data (schools, parks, transit, amenities)...")
    osm_scraper = OSMScraper()
    await osm_scraper.collect_all()

    elapsed = time.time() - start
    logger.info(f"\nData collection complete in {elapsed:.1f}s")
    logger.info("Processed files are in data/processed/")


def main():
    asyncio.run(collect_all())


if __name__ == "__main__":
    main()
