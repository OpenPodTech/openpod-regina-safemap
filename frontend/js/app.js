/**
 * Regina SafeMap — App Entry Point
 * Initializes map, loads data, wires up interactions.
 */

(async function () {
    'use strict';

    // Initialize map
    initMap();

    // Wire up layer toggle buttons
    document.querySelectorAll('.layer-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const layerName = btn.dataset.layer;
            btn.classList.toggle('active');
            toggleLayer(layerName);
        });
    });

    // Wire up panel close button
    document.getElementById('panel-close').addEventListener('click', hidePanel);

    // Wire up search
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', handleSearch);
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            handleSearchSubmit();
        }
    });

    // Load data from API (or fallback to static files)
    await loadAllData();
})();

// ─── Data Loading ────────────────────────────────────────────────

async function loadAllData() {
    try {
        // Try API first, fall back to static GeoJSON files
        const [neighbourhoods, crimes, schools, transit, amenities, parks] = await Promise.allSettled([
            fetchData('/neighbourhoods'),
            fetchData('/crimes'),
            fetchData('/schools'),
            fetchData('/transit'),
            fetchData('/amenities'),
            fetchData('/parks'),
        ]);

        if (neighbourhoods.status === 'fulfilled' && neighbourhoods.value) {
            loadNeighbourhoods(neighbourhoods.value);
        }
        if (crimes.status === 'fulfilled' && crimes.value) {
            loadCrimeHeatmap(crimes.value);
        }
        if (schools.status === 'fulfilled' && schools.value) {
            loadSchools(schools.value);
        }
        if (transit.status === 'fulfilled' && transit.value) {
            loadTransit(transit.value);
        }
        if (amenities.status === 'fulfilled' && amenities.value) {
            loadAmenities(amenities.value);
        }
        if (parks.status === 'fulfilled' && parks.value) {
            loadParks(parks.value);
        }
    } catch (err) {
        console.warn('Failed to load data from API, trying static files...', err);
        await loadStaticData();
    }
}

async function fetchData(endpoint) {
    // Static file mapping (works on GitHub Pages and locally)
    const staticMap = {
        '/neighbourhoods': 'neighbourhoods_scored.geojson',
        '/crimes': 'crimes.geojson',
        '/schools': 'schools.geojson',
        '/transit': 'transit_stops.geojson',
        '/amenities': 'amenities.geojson',
        '/parks': 'parks.geojson',
    };

    // Try API endpoint first (local dev with FastAPI)
    try {
        const response = await fetch(`${CONFIG.API_BASE}${endpoint}`);
        if (response.ok) {
            return await response.json();
        }
    } catch (e) {
        // API not available, use static files
    }

    // Load from static data directory (GitHub Pages deployment)
    const filename = staticMap[endpoint];
    if (filename) {
        const paths = [
            `${CONFIG.STATIC_DATA}/${filename}`,
            `./data/processed/${filename}`,
            `../data/processed/${filename}`,
        ];

        for (const path of paths) {
            try {
                const response = await fetch(path);
                if (response.ok) {
                    return await response.json();
                }
            } catch (e) {
                continue;
            }
        }

        // Fallback: try un-scored neighbourhoods
        if (endpoint === '/neighbourhoods') {
            for (const path of [`${CONFIG.STATIC_DATA}/neighbourhoods.geojson`, `./data/processed/neighbourhoods.geojson`]) {
                try {
                    const response = await fetch(path);
                    if (response.ok) return await response.json();
                } catch (e) { continue; }
            }
        }
    }

    console.debug(`No data available for ${endpoint}`);
    return null;
}

async function loadStaticData() {
    // Direct static loading as final fallback
    console.info('Running in static mode — run scrapers to populate data');
}

// ─── Search ──────────────────────────────────────────────────────

let searchTimeout = null;

function handleSearch(e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        const query = e.target.value.trim();
        if (query.length >= 3) {
            highlightSearchResults(query);
        }
    }, 300);
}

function handleSearchSubmit() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    const result = findNeighbourhoodByName(query);
    if (result) {
        selectNeighbourhood(result.layer, result.feature);
    }
}

function highlightSearchResults(query) {
    const result = findNeighbourhoodByName(query);
    if (result) {
        // Briefly highlight the found neighbourhood
        result.layer.setStyle({
            fillColor: '#d29922',
            fillOpacity: 0.3,
            color: '#d29922',
            weight: 2,
        });

        // Reset after 2 seconds if not selected
        setTimeout(() => {
            if (result.layer !== selectedNeighbourhood) {
                result.layer.setStyle(CONFIG.NEIGHBOURHOOD_STYLE.default);
            }
        }, 2000);
    }
}
