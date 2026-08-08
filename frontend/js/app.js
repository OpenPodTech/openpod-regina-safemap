/**
 * Regina SafeMap — App Entry Point
 * Search-first, clean interactions.
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
    const searchDropdown = document.getElementById('search-dropdown');

    searchInput.addEventListener('input', handleSearch);
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            handleSearchSubmit();
            searchDropdown.classList.remove('visible');
        }
        if (e.key === 'Escape') {
            searchDropdown.classList.remove('visible');
        }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            searchDropdown.classList.remove('visible');
        }
    });

    // Wire up popular neighbourhood links
    document.querySelectorAll('.popular-link').forEach((link) => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const name = link.dataset.neighbourhood;
            if (name) {
                searchInput.value = name;
                const result = findNeighbourhoodByName(name);
                if (result) {
                    selectNeighbourhood(result.layer, result.feature);
                }
            }
        });
    });

    // Load data
    await loadAllData();
})();

// ─── Data Loading ────────────────────────────────────────────────

async function loadAllData() {
    try {
        const [neighbourhoods, crimes, schools, transit, amenities, parks, crimeStats, descriptions] = await Promise.allSettled([
            fetchData('/neighbourhoods'),
            fetchData('/crimes'),
            fetchData('/schools'),
            fetchData('/transit'),
            fetchData('/amenities'),
            fetchData('/parks'),
            fetchData('/crime_stats'),
            fetchData('/descriptions'),
        ]);

        // Store globally for panel use
        window.crimeStats = crimeStats.status === 'fulfilled' ? crimeStats.value : null;
        window.descriptions = descriptions.status === 'fulfilled' ? descriptions.value : null;

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
        console.warn('Failed to load data:', err);
    }
}

async function fetchData(endpoint) {
    const staticMap = {
        '/neighbourhoods': 'neighbourhoods_scored.geojson',
        '/crimes': 'crimes.geojson',
        '/schools': 'schools.geojson',
        '/transit': 'transit_stops.geojson',
        '/amenities': 'amenities.geojson',
        '/parks': 'parks.geojson',
        '/crime_stats': 'crime_stats.json',
        '/descriptions': 'descriptions.json',
    };

    // Try API endpoint first
    try {
        const response = await fetch(`${CONFIG.API_BASE}${endpoint}`);
        if (response.ok) return await response.json();
    } catch (e) { /* API not available */ }

    // Load from static data directory
    const filename = staticMap[endpoint];
    if (filename) {
        const paths = [
            `${CONFIG.STATIC_DATA}/${filename}`,
            `./data/processed/${filename}`,
        ];

        for (const path of paths) {
            try {
                const response = await fetch(path);
                if (response.ok) return await response.json();
            } catch (e) { continue; }
        }

        // Fallback: try un-scored neighbourhoods
        if (endpoint === '/neighbourhoods') {
            try {
                const response = await fetch(`${CONFIG.STATIC_DATA}/neighbourhoods.geojson`);
                if (response.ok) return await response.json();
            } catch (e) { /* no fallback */ }
        }
    }

    return null;
}

// ─── Search ──────────────────────────────────────────────────────

let searchTimeout = null;

function handleSearch(e) {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();
    const dropdown = document.getElementById('search-dropdown');

    if (query.length < 2) {
        dropdown.classList.remove('visible');
        return;
    }

    searchTimeout = setTimeout(() => {
        const results = findAllNeighbourhoodsByName(query);
        renderSearchDropdown(results);
    }, 150);
}

function handleSearchSubmit() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) return;

    const result = findNeighbourhoodByName(query);
    if (result) {
        selectNeighbourhood(result.layer, result.feature);
    }
}

function findAllNeighbourhoodsByName(query) {
    if (!neighbourhoodLayer) return [];

    const results = [];
    neighbourhoodLayer.eachLayer((layer) => {
        const name = layer.feature.properties.name || '';
        if (name.toLowerCase().includes(query.toLowerCase())) {
            results.push({ layer, feature: layer.feature, name });
        }
    });

    return results.slice(0, 8); // Cap at 8 results
}

function renderSearchDropdown(results) {
    const dropdown = document.getElementById('search-dropdown');

    if (results.length === 0) {
        dropdown.classList.remove('visible');
        return;
    }

    dropdown.innerHTML = results.map((r) => {
        const props = r.feature.properties;
        const score = props.overall || props.safety || 0;
        let scoreClass = 'score-yellow';
        if (score >= 70) scoreClass = 'score-green';
        else if (score < 50) scoreClass = 'score-red';

        return `<div class="search-result" data-name="${r.name}">
            <span class="search-result-name">${r.name}</span>
            ${score > 0 ? `<span class="search-result-score ${scoreClass}">${score}/100</span>` : ''}
        </div>`;
    }).join('');

    // Wire up clicks
    dropdown.querySelectorAll('.search-result').forEach((el) => {
        el.addEventListener('click', () => {
            const name = el.dataset.name;
            document.getElementById('search-input').value = name;
            dropdown.classList.remove('visible');
            const result = findNeighbourhoodByName(name);
            if (result) {
                selectNeighbourhood(result.layer, result.feature);
            }
        });
    });

    dropdown.classList.add('visible');
}
