/**
 * Regina SafeMap — Configuration
 * OpenPodTech · Premium Palette
 */

const CONFIG = {
    // API base URL
    API_BASE: window.location.hostname === 'localhost'
        ? 'http://localhost:8000/api'
        : '/api',

    // Static data path (GitHub Pages deployment)
    STATIC_DATA: './data/processed',

    // Map settings
    MAP_CENTER: [50.4452, -104.6189],
    MAP_ZOOM: 12,
    MAP_MIN_ZOOM: 10,
    MAP_MAX_ZOOM: 18,

    // Map tile layer (dark mode)
    TILE_URL: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    TILE_ATTRIBUTION: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> | <a href="https://carto.com/">CARTO</a> | <a href="https://github.com/OpenPodTech">OpenPod</a>',

    // Heatmap settings
    HEATMAP: {
        radius: 22,
        blur: 22,
        maxZoom: 14,
        max: 0.6,
        gradient: {
            0.0: '#10b981',
            0.2: '#34d399',
            0.4: '#f59e0b',
            0.6: '#f97316',
            0.8: '#ef4444',
            1.0: '#7f1d1d',
        },
    },

    // Marker colours by category
    MARKERS: {
        school: { color: '#a78bfa', icon: '\u{1F3EB}' },
        park: { color: '#10b981', icon: '\u{1F333}' },
        transit: { color: '#0EA5E9', icon: '\u{1F68C}' },
        grocery: { color: '#f97316', icon: '\u{1F6D2}' },
        healthcare: { color: '#ef4444', icon: '\u{1F3E5}' },
        community: { color: '#f59e0b', icon: '\u{1F4DA}' },
    },

    // Neighbourhood polygon style
    NEIGHBOURHOOD_STYLE: {
        default: {
            fillColor: '#0EA5E9',
            fillOpacity: 0.03,
            color: 'rgba(255, 255, 255, 0.08)',
            weight: 1,
        },
        hover: {
            fillColor: '#0EA5E9',
            fillOpacity: 0.12,
            color: '#0EA5E9',
            weight: 2,
        },
        selected: {
            fillColor: '#0EA5E9',
            fillOpacity: 0.18,
            color: '#0EA5E9',
            weight: 2.5,
        },
    },

    // Score grade thresholds
    GRADES: [
        { min: 90, grade: 'A+', color: '#10b981' },
        { min: 80, grade: 'A', color: '#34d399' },
        { min: 70, grade: 'B', color: '#0EA5E9' },
        { min: 60, grade: 'C', color: '#f59e0b' },
        { min: 50, grade: 'D', color: '#f97316' },
        { min: 0, grade: 'F', color: '#ef4444' },
    ],
};
