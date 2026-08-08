/**
 * Regina SafeMap — Map Initialization
 * Sets up the Leaflet map with dark tile layer.
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

    // Dark tile layer
    L.tileLayer(CONFIG.TILE_URL, {
        attribution: CONFIG.TILE_ATTRIBUTION,
        subdomains: 'abcd',
        maxZoom: CONFIG.MAP_MAX_ZOOM,
    }).addTo(map);

    // Move zoom controls to bottom-right
    map.zoomControl.setPosition('bottomright');
}

function loadNeighbourhoods(geojson) {
    if (neighbourhoodLayer) {
        map.removeLayer(neighbourhoodLayer);
    }

    neighbourhoodLayer = L.geoJSON(geojson, {
        style: () => CONFIG.NEIGHBOURHOOD_STYLE.default,
        onEachFeature: (feature, layer) => {
            const name = feature.properties.name || 'Unknown';

            layer.on('mouseover', () => {
                if (layer !== selectedNeighbourhood) {
                    layer.setStyle(CONFIG.NEIGHBOURHOOD_STYLE.hover);
                }
            });

            layer.on('mouseout', () => {
                if (layer !== selectedNeighbourhood) {
                    layer.setStyle(CONFIG.NEIGHBOURHOOD_STYLE.default);
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
        selectedNeighbourhood.setStyle(CONFIG.NEIGHBOURHOOD_STYLE.default);
    }

    // Highlight new selection
    selectedNeighbourhood = layer;
    layer.setStyle(CONFIG.NEIGHBOURHOOD_STYLE.selected);

    // Fit map to neighbourhood
    map.fitBounds(layer.getBounds(), { padding: [50, 400] });

    // Show info panel
    showPanel(feature.properties);
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
