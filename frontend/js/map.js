/**
 * Regina SafeMap — Map Initialization
 * Light tiles, safety-coloured polygons, clean interactions.
 */

let map;
let neighbourhoodLayer;
let selectedNeighbourhood = null;

function initMap() {
    map = L.map('map', {
        center: CONFIG.MAP_CENTER,
        zoom: CONFIG.MAP_ZOOM,
        minZoom: CONFIG.MAP_MIN_ZOOM,
        maxZoom: CONFIG.MAP_MAX_ZOOM,
        zoomControl: true,
        attributionControl: true,
    });

    // Light tile layer
    L.tileLayer(CONFIG.TILE_URL, {
        attribution: CONFIG.TILE_ATTRIBUTION,
        subdomains: 'abcd',
        maxZoom: CONFIG.MAP_MAX_ZOOM,
    }).addTo(map);

    // Move zoom controls to bottom-right
    map.zoomControl.setPosition('bottomright');
}

function getNeighbourhoodStyle(feature) {
    // Determine fill colour based on crime data
    const props = feature.properties;
    let incidents = props.total_crimes || props.total_incidents || 0;

    // Also check global crime stats
    if (window.crimeStats && props.name && window.crimeStats[props.name]) {
        incidents = window.crimeStats[props.name].total_incidents || incidents;
    }

    let fillColor = CONFIG.SAFETY_COLORS.unknown.fill;
    let borderColor = CONFIG.SAFETY_COLORS.unknown.border;

    if (incidents > 0) {
        if (incidents < CONFIG.SAFETY_THRESHOLDS.safe) {
            fillColor = CONFIG.SAFETY_COLORS.safe.fill;
            borderColor = CONFIG.SAFETY_COLORS.safe.border;
        } else if (incidents < CONFIG.SAFETY_THRESHOLDS.moderate) {
            fillColor = CONFIG.SAFETY_COLORS.moderate.fill;
            borderColor = CONFIG.SAFETY_COLORS.moderate.border;
        } else {
            fillColor = CONFIG.SAFETY_COLORS.high.fill;
            borderColor = CONFIG.SAFETY_COLORS.high.border;
        }
    }

    return {
        fillColor: fillColor,
        fillOpacity: 0.18,
        color: borderColor,
        weight: 1.5,
    };
}

function loadNeighbourhoods(geojson) {
    if (neighbourhoodLayer) {
        map.removeLayer(neighbourhoodLayer);
    }

    neighbourhoodLayer = L.geoJSON(geojson, {
        style: (feature) => getNeighbourhoodStyle(feature),
        onEachFeature: (feature, layer) => {
            const name = feature.properties.name || 'Unknown';
            const baseStyle = getNeighbourhoodStyle(feature);

            layer.on('mouseover', () => {
                if (layer !== selectedNeighbourhood) {
                    layer.setStyle({
                        ...baseStyle,
                        fillOpacity: 0.35,
                        color: '#0EA5E9',
                        weight: 2,
                    });
                }
            });

            layer.on('mouseout', () => {
                if (layer !== selectedNeighbourhood) {
                    layer.setStyle(baseStyle);
                }
            });

            layer.on('click', () => {
                selectNeighbourhood(layer, feature);
            });

            // Tooltip with name
            layer.bindTooltip(name, {
                sticky: true,
                className: 'neighbourhood-tooltip',
            });
        },
    }).addTo(map);
}

function selectNeighbourhood(layer, feature) {
    // Reset previous selection
    if (selectedNeighbourhood) {
        const prevFeature = selectedNeighbourhood.feature;
        selectedNeighbourhood.setStyle(getNeighbourhoodStyle(prevFeature));
    }

    // Highlight new selection
    selectedNeighbourhood = layer;
    const baseStyle = getNeighbourhoodStyle(feature);
    layer.setStyle({
        ...baseStyle,
        fillOpacity: 0.3,
        color: '#0EA5E9',
        weight: 2.5,
    });

    // Fit map to neighbourhood
    map.fitBounds(layer.getBounds(), { padding: [50, 400] });

    // Show info panel
    showPanel(feature.properties);

    // Update profile link
    const profileLink = document.getElementById('panel-profile-link');
    if (profileLink && feature.properties.name) {
        const slug = feature.properties.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        profileLink.href = `neighbourhoods/${slug}.html`;
    }
}

function findNeighbourhoodByName(name) {
    if (!neighbourhoodLayer) return null;

    let found = null;
    neighbourhoodLayer.eachLayer((layer) => {
        const layerName = layer.feature.properties.name || '';
        if (layerName.toLowerCase().includes(name.toLowerCase())) {
            found = { layer, feature: layer.feature };
        }
    });
    return found;
}
