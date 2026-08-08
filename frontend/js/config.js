/**
 * Regina SafeMap — Configuration
 * OpenPodTech · Light, clean, readable
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

    // Map tile layer — LIGHT (readable in sunlight)
    TILE_URL: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    TILE_ATTRIBUTION: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> | <a href="https://carto.com/">CARTO</a> | <a href="https://github.com/OpenPodTech">OpenPod</a>',

    // Heatmap settings (subtle, not screaming)
    HEATMAP: {
        radius: 20,
        blur: 25,
        maxZoom: 14,
        max: 0.8,
        gradient: {
            0.0: 'rgba(16, 185, 129, 0)',
            0.2: 'rgba(16, 185, 129, 0.3)',
            0.4: 'rgba(245, 158, 11, 0.4)',
            0.6: 'rgba(249, 115, 22, 0.5)',
            0.8: 'rgba(239, 68, 68, 0.5)',
            1.0: 'rgba(239, 68, 68, 0.6)',
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

    // Neighbourhood polygon styles — safety-based colouring
    NEIGHBOURHOOD_STYLE: {
        default: {
            fillColor: '#94a3b8',
            fillOpacity: 0.08,
            color: '#cbd5e1',
            weight: 1.5,
        },
        hover: {
            fillOpacity: 0.2,
            color: '#0EA5E9',
            weight: 2,
        },
        selected: {
            fillOpacity: 0.25,
            color: '#0EA5E9',
            weight: 2.5,
        },
    },

    // Safety-based fill colours for polygons
    SAFETY_COLORS: {
        safe: { fill: '#10b981', border: '#059669' },       // green
        moderate: { fill: '#f59e0b', border: '#d97706' },   // yellow
        high: { fill: '#ef4444', border: '#dc2626' },       // red
        unknown: { fill: '#94a3b8', border: '#64748b' },    // grey
    },

    // Thresholds for safety colouring (incident counts)
    SAFETY_THRESHOLDS: {
        safe: 50,       // < 50 incidents = green
        moderate: 200,  // < 200 = yellow, >= 200 = red
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
