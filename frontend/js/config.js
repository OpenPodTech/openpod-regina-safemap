/**
 * Regina SafeMap — Configuration
 */

const CONFIG = {
    // API base URL
    // On GitHub Pages: loads static GeoJSON from /data/processed/
    // Locally with FastAPI: uses /api endpoints
    API_BASE: window.location.hostname === 'localhost'
        ? 'http://localhost:8000/api'
        : '/api',

    // Static data path (GitHub Pages deployment)
    STATIC_DATA: './data/processed',

    // Map settings
    MAP_CENTER: [50.4452, -104.6189],   // Regina city centre
    MAP_ZOOM: 12,
    MAP_MIN_ZOOM: 10,
    MAP_MAX_ZOOM: 18,

    // Map tile layer (dark mode for the aesthetic)
    TILE_URL: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    TILE_ATTRIBUTION: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> | <a href="https://carto.com/">CARTO</a> | <a href="https://github.com/OpenPodHQ">OpenPod</a>',

    // Heatmap settings
    HEATMAP: {
        radius: 20,
        blur: 20,
        maxZoom: 14,
        max: 0.6,
        gradient: {
            0.0: '#2ea043',
            0.2: '#56d364',
            0.4: '#d29922',
            0.6: '#f0883e',
            0.8: '#f85149',
            1.0: '#a40e26',
        },
    },

    // Marker colours by category
    MARKERS: {
        school: { color: '#a371f7', icon: '🏫' },
        park: { color: '#3fb950', icon: '🌳' },
        transit: { color: '#58a6ff', icon: '🚌' },
        grocery: { color: '#f0883e', icon: '🛒' },
        healthcare: { color: '#f85149', icon: '🏥' },
        community: { color: '#d29922', icon: '📚' },
    },

    // Neighbourhood polygon style
    NEIGHBOURHOOD_STYLE: {
        default: {
            fillColor: '#1f6feb',
            fillOpacity: 0.05,
            color: '#30363d',
            weight: 1,
        },
        hover: {
            fillColor: '#58a6ff',
            fillOpacity: 0.15,
            color: '#58a6ff',
            weight: 2,
        },
        selected: {
            fillColor: '#58a6ff',
            fillOpacity: 0.2,
            color: '#58a6ff',
            weight: 3,
        },
    },

    // Score grade thresholds
    GRADES: [
        { min: 90, grade: 'A+', color: '#2ea043' },
        { min: 80, grade: 'A', color: '#3fb950' },
        { min: 70, grade: 'B', color: '#56d364' },
        { min: 60, grade: 'C', color: '#d29922' },
        { min: 50, grade: 'D', color: '#f0883e' },
        { min: 0, grade: 'F', color: '#f85149' },
    ],
};
