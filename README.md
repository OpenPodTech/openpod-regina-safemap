# OpenPod Regina SafeMap

**Know your neighbourhood before you move. One map, everything that matters.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![OpenPod](https://img.shields.io/badge/OpenPod-civic%20tech-blue.svg)](https://github.com/OpenPodHQ)

---

## The Problem

You're moving to Regina — maybe you're an immigrant family from India, a young couple buying your first home, or someone relocating for work. You need to know:

- **Is this neighbourhood safe?** Where are the break-ins, the assaults, the vehicle thefts?
- **What's nearby?** Schools, grocery stores, parks, bus routes, clinics?
- **Is it getting better or worse?** Crime trending up or down over the past 3 years?
- **What do people actually experience?** Not just stats — the real character of the area?

Right now, this information is scattered across:
- Regina Police crime map (hard to read, no context)
- Google Maps (no crime data, no scoring)
- Realtor websites (biased — they want to sell you the house)
- Word of mouth (unreliable, often outdated or prejudiced)

**Nobody puts it all together in one place.** Until now.

## The Solution

Regina SafeMap is a free, open-source neighbourhood intelligence tool that overlays:

1. **Crime heatmap** — Real police-reported crime data, visualized by type and density
2. **Neighbourhood scores** — Safety, walkability, transit access, schools, amenities (0-100)
3. **School proximity** — Every school with distance, ratings, and type (public/catholic/french)
4. **Amenities layer** — Grocery, healthcare, parks, gyms, libraries, community centres
5. **Transit access** — Bus routes, stops, frequency
6. **Trend arrows** — Is crime going up or down in this area? Getting better or worse?

All on one interactive map. Click any neighbourhood. Get the full picture.

---

## Demo

```
+----------------------------------------------------+
|  🗺️ REGINA SAFEMAP                    [Search...]  |
|----------------------------------------------------|
|                                                    |
|     [Crime] [Schools] [Transit] [Amenities]        |
|                                                    |
|         ┌─────────────────────────┐                |
|         │    Cathedral    ◀──────── Safety: 62/100 |
|         │    ████████░░           │ Schools: 85    |
|         │   ▲ Improving (+8%)     │ Transit: 91    |
|         └─────────────────────────┘ Amenity: 88    |
|                                                    |
|    [Harbour Landing]  [Lakeview]  [North Central]  |
|                                                    |
+----------------------------------------------------+
```

---

## Data Sources

| Source | Data | License | Update Frequency |
|--------|------|---------|------------------|
| [Regina Police Crime Map](https://reginapolice.ca) | Reported incidents by type & location | Public | Monthly |
| [OpenRegina.ca](https://openregina.ca) | 1,300+ city datasets — boundaries, zoning, permits | Open Government Licence | Varies |
| [City of Regina GIS](https://opengis.regina.ca) | Neighbourhood boundaries, infrastructure | Open | Static |
| [OpenStreetMap](https://openstreetmap.org) | Schools, parks, businesses, transit stops | ODbL | Live |
| [GitHub: regina-crime-data](https://github.com/andrewjdyck/regina-crime-data) | Historical crime CSVs by neighbourhood | Open | Annual |
| [Statistics Canada](https://statcan.gc.ca) | Census data, demographics | Open | Census years |

All data is publicly available under open licences. No scraping of private data. No personal information collected.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      FRONTEND                             │
│  Leaflet.js map + heatmap.js + neighbourhood panels      │
│  Pure HTML/CSS/JS — no framework, deploys anywhere       │
└────────────────────────────┬─────────────────────────────┘
                             │ API calls
┌────────────────────────────┴─────────────────────────────┐
│                      BACKEND API                          │
│  FastAPI (Python) — serves GeoJSON, scores, profiles     │
│  Endpoints: /neighbourhoods, /crimes, /scores, /search   │
└────────────────────────────┬─────────────────────────────┘
                             │ reads
┌────────────────────────────┴─────────────────────────────┐
│                    DATA LAYER                             │
│  SQLite + GeoJSON files                                  │
│  Scrapers run on schedule (cron/GitHub Actions)          │
└────────────────────────────┬─────────────────────────────┘
                             │ fetches
┌────────────────────────────┴─────────────────────────────┐
│                  EXTERNAL SOURCES                         │
│  RPS Crime Map | OpenRegina | OSM Overpass | StatsCan    │
└──────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Leaflet.js + leaflet-heat | Lightweight, mobile-friendly, no React bloat |
| Backend | FastAPI (Python) | Fast, async, easy to deploy |
| Database | SQLite + GeoJSON | Simple, portable, no server needed |
| Scrapers | Python (httpx + BeautifulSoup) | Collect and normalize public data |
| Scoring | Python (pandas + numpy) | Neighbourhood scoring algorithm |
| Hosting | GitHub Pages (frontend) + Railway/Render (API) | Free tier works |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js (optional, for frontend dev server)

### Backend Setup

```bash
cd src
pip install -r requirements.txt

# Collect initial data
python -m scrapers.collect_all

# Start API server
uvicorn api.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
# Just open index.html in a browser, or:
python -m http.server 3000
```

Visit `http://localhost:3000` — the map loads with Regina neighbourhoods and crime data.

---

## Project Structure

```
openpod-regina-safemap/
├── README.md
├── LICENSE
├── requirements.txt
├── src/
│   ├── scrapers/           ← Data collection
│   │   ├── crime_scraper.py      — RPS crime map data
│   │   ├── neighbourhood_scraper.py — OpenRegina boundaries
│   │   ├── osm_scraper.py        — Schools, parks, transit from OSM
│   │   └── collect_all.py        — Run all scrapers
│   ├── scoring/            ← Neighbourhood scoring
│   │   ├── calculator.py         — Main scoring algorithm
│   │   └── weights.py            — Configurable score weights
│   └── api/                ← Backend API
│       ├── main.py               — FastAPI app
│       ├── routes.py             — API endpoints
│       └── models.py             — Data models
├── frontend/               ← Web interface
│   ├── index.html                — Main page
│   ├── css/style.css             — Styling
│   └── js/
│       ├── map.js                — Leaflet map setup
│       ├── layers.js             — Crime, school, transit layers
│       └── panels.js             — Neighbourhood info panels
├── data/
│   ├── raw/                      — Unprocessed downloads
│   └── processed/                — Ready-to-serve GeoJSON + scores
└── .github/
    └── workflows/
        └── update-data.yml       — Weekly data refresh via GitHub Actions
```

---

## Neighbourhood Scoring

Each neighbourhood gets a score from 0-100 across five dimensions:

| Dimension | Weight | Factors |
|-----------|--------|---------|
| **Safety** | 30% | Crime density, crime type severity, year-over-year trend |
| **Schools** | 20% | Number within 1km, types available, elementary + high school coverage |
| **Transit** | 20% | Bus stops within 500m, route frequency, connection to downtown |
| **Amenities** | 20% | Grocery, healthcare, parks, libraries, recreation within 1km |
| **Walkability** | 10% | Sidewalk coverage, intersection density, distance to daily needs |

**Overall Score** = weighted average, displayed as a single number + letter grade (A through F).

---

## Who This Is For

- **Immigrants & newcomers** — "I just arrived from India/Philippines/Ukraine. Where should I live?"
- **First-time homebuyers** — "Is this $280K house in a good area?"
- **Renters** — "I found a cheap apartment on North Central. Should I be worried?"
- **Families** — "Where are the best schools within walking distance?"
- **Real estate agents** — Use it to give clients honest neighbourhood context
- **City planners** — See where investment is needed most

---

## Contributing

This is for Regina, by people who live here. We need:

- **Data validation** — Do the crime stats match your experience? Report inaccuracies.
- **Neighbourhood knowledge** — Add context that data can't capture (community events, hidden gems)
- **Design** — Make the map beautiful and intuitive on mobile
- **Data sources** — Know of more public data? Open an issue.
- **Other cities** — Want to fork this for Saskatoon, Winnipeg, Edmonton? Go for it.

---

## Privacy & Ethics

- **No personal data collected** — We don't track users, no cookies, no analytics
- **No exact crime locations** — All data is aggregated by neighbourhood/block, never pinpoints addresses
- **No profiling** — We show facts, not stereotypes. Data without judgment.
- **Trend matters more than snapshot** — A neighbourhood improving from bad is BETTER than one declining from good
- **Open Government data only** — Everything we use is already public

---

## Forking for Other Cities

This tool is designed to be forked. If you want SafeMap for your city:

1. Fork this repo
2. Replace the scraper configurations with your city's data sources
3. Update neighbourhood boundaries GeoJSON
4. Adjust scoring weights for your context
5. Deploy

Cities with compatible data: Saskatoon, Winnipeg, Edmonton, Calgary, Ottawa, Vancouver.

---

## License

MIT — Use it, fork it, sell it, whatever helps people.

---

*Built by [OpenPod](https://github.com/OpenPodHQ) — civic tech from Regina, Saskatchewan.*

*"Upcoming families deserve to know what they're walking into. Not after they sign the lease — before."*
