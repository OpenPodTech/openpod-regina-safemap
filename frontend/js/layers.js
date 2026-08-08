/**
 * Regina SafeMap — Data Layers
 * Manages crime heatmap, schools, transit, amenities, and parks.
 */

let heatmapLayer = null;
let schoolsLayer = null;
let transitLayer = null;
let amenitiesLayer = null;
let parksLayer = null;

// Track active layers
const activeLayers = new Set(['crime']);

// ─── Crime Heatmap ───────────────────────────────────────────────

function loadCrimeHeatmap(crimeData) {
    if (heatmapLayer) {
        map.removeLayer(heatmapLayer);
    }

    const heatPoints = [];
    crimeData.features.forEach((feature) => {
        const coords = feature.geometry.coordinates;
        const severity = feature.properties.severity || 2;
        const count = feature.properties.count || 1;
        // Intensity = severity * count (capped)
        const intensity = Math.min(severity * count * 0.1, 1.0);
        heatPoints.push([coords[1], coords[0], intensity]);
    });

    heatmapLayer = L.heatLayer(heatPoints, CONFIG.HEATMAP);

    if (activeLayers.has('crime')) {
        heatmapLayer.addTo(map);
    }
}

// ─── Schools Layer ───────────────────────────────────────────────

function loadSchools(schoolsData) {
    if (schoolsLayer) {
        map.removeLayer(schoolsLayer);
    }

    schoolsLayer = L.layerGroup();

    schoolsData.features.forEach((feature) => {
        const coords = feature.geometry.coordinates;
        const props = feature.properties;

        const marker = L.circleMarker([coords[1], coords[0]], {
            radius: 7,
            fillColor: CONFIG.MARKERS.school.color,
            fillOpacity: 0.8,
            color: '#ffffff',
            weight: 1,
        });

        marker.bindPopup(`
            <strong>${props.name}</strong><br>
            Type: ${props.school_type || 'Public'}<br>
            ${props.operator ? `Operator: ${props.operator}<br>` : ''}
            ${props.website ? `<a href="${props.website}" target="_blank">Website</a>` : ''}
        `);

        schoolsLayer.addLayer(marker);
    });

    if (activeLayers.has('schools')) {
        schoolsLayer.addTo(map);
    }
}

// ─── Transit Layer ───────────────────────────────────────────────

function loadTransit(transitData) {
    if (transitLayer) {
        map.removeLayer(transitLayer);
    }

    transitLayer = L.layerGroup();

    transitData.features.forEach((feature) => {
        const coords = feature.geometry.coordinates;
        const props = feature.properties;

        const marker = L.circleMarker([coords[1], coords[0]], {
            radius: 4,
            fillColor: CONFIG.MARKERS.transit.color,
            fillOpacity: 0.7,
            color: '#ffffff',
            weight: 1,
        });

        marker.bindPopup(`
            <strong>${props.name}</strong><br>
            ${props.ref ? `Stop #${props.ref}<br>` : ''}
            ${props.routes ? `Routes: ${props.routes}<br>` : ''}
            Shelter: ${props.shelter || 'no'}
        `);

        transitLayer.addLayer(marker);
    });

    if (activeLayers.has('transit')) {
        transitLayer.addTo(map);
    }
}

// ─── Amenities Layer ─────────────────────────────────────────────

function loadAmenities(amenityData) {
    if (amenitiesLayer) {
        map.removeLayer(amenitiesLayer);
    }

    amenitiesLayer = L.layerGroup();

    amenityData.features.forEach((feature) => {
        const coords = feature.geometry.coordinates;
        const props = feature.properties;
        const category = props.category || 'other';
        const markerConfig = CONFIG.MARKERS[category] || { color: '#8b949e', icon: '📍' };

        const marker = L.circleMarker([coords[1], coords[0]], {
            radius: 6,
            fillColor: markerConfig.color,
            fillOpacity: 0.7,
            color: '#ffffff',
            weight: 1,
        });

        marker.bindPopup(`
            <strong>${props.name}</strong><br>
            Type: ${props.type}<br>
            ${props.opening_hours ? `Hours: ${props.opening_hours}<br>` : ''}
            ${props.phone ? `Phone: ${props.phone}<br>` : ''}
            ${props.website ? `<a href="${props.website}" target="_blank">Website</a>` : ''}
        `);

        amenitiesLayer.addLayer(marker);
    });

    if (activeLayers.has('amenities')) {
        amenitiesLayer.addTo(map);
    }
}

// ─── Parks Layer ─────────────────────────────────────────────────

function loadParks(parksData) {
    if (parksLayer) {
        map.removeLayer(parksLayer);
    }

    parksLayer = L.layerGroup();

    parksData.features.forEach((feature) => {
        const coords = feature.geometry.coordinates;
        const props = feature.properties;

        const marker = L.circleMarker([coords[1], coords[0]], {
            radius: 6,
            fillColor: CONFIG.MARKERS.park.color,
            fillOpacity: 0.7,
            color: '#ffffff',
            weight: 1,
        });

        marker.bindPopup(`
            <strong>${props.name}</strong><br>
            Type: ${props.type}<br>
            ${props.sport ? `Sport: ${props.sport}<br>` : ''}
        `);

        parksLayer.addLayer(marker);
    });

    if (activeLayers.has('parks')) {
        parksLayer.addTo(map);
    }
}

// ─── Layer Toggle ────────────────────────────────────────────────

function toggleLayer(layerName) {
    const layerMap = {
        crime: heatmapLayer,
        schools: schoolsLayer,
        transit: transitLayer,
        amenities: amenitiesLayer,
        parks: parksLayer,
    };

    const layer = layerMap[layerName];
    if (!layer) return;

    if (activeLayers.has(layerName)) {
        activeLayers.delete(layerName);
        map.removeLayer(layer);
    } else {
        activeLayers.add(layerName);
        layer.addTo(map);
    }
}
