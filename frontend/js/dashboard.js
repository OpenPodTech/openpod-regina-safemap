/**
 * Dashboard — Populates quick picks and data freshness
 * Loads crime_stats.json for the "At a glance" section.
 */
(function () {
    'use strict';

    function loadData() {
        var statsPromise = fetch('data/processed/crime_stats.json')
            .then(function (r) { return r.ok ? r.json() : null; })
            .catch(function () { return null; });

        var trendsPromise = fetch('data/processed/trends.json')
            .then(function (r) { return r.ok ? r.json() : null; })
            .catch(function () { return null; });

        Promise.all([statsPromise, trendsPromise]).then(function (results) {
            var crimeStats = results[0];
            var trendsData = results[1];
            if (crimeStats) populateQuickPicks(crimeStats, trendsData);
        });
    }

    function populateQuickPicks(crimeStats, trendsData) {
        var totalIncidents = 0;
        var safest = { name: '--', count: Infinity };
        var hottest = { name: '--', count: 0 };
        var improving = { name: '--', change: 0 };

        for (var hood in crimeStats) {
            if (!crimeStats.hasOwnProperty(hood)) continue;
            var data = crimeStats[hood];
            var count = data.total_incidents || 0;
            totalIncidents += count;

            if (count < safest.count && count > 0) {
                safest = { name: hood, count: count };
            }
            if (count > hottest.count) {
                hottest = { name: hood, count: count };
            }
            if (data.yoy_change_pct && data.yoy_change_pct < improving.change) {
                improving = { name: hood, change: data.yoy_change_pct };
            }
        }

        // Populate safest
        var safestEl = document.getElementById('pick-safest');
        var safestDetail = document.getElementById('pick-safest-detail');
        if (safestEl) safestEl.textContent = safest.name;
        if (safestDetail) safestDetail.textContent = safest.count + ' incidents';

        // Populate hottest
        var hottestEl = document.getElementById('pick-hottest');
        var hottestDetail = document.getElementById('pick-hottest-detail');
        if (hottestEl) hottestEl.textContent = hottest.name;
        if (hottestDetail) hottestDetail.textContent = hottest.count.toLocaleString() + ' incidents';

        // Populate improving
        var improvingEl = document.getElementById('pick-improving');
        var improvingDetail = document.getElementById('pick-improving-detail');
        if (improvingEl) improvingEl.textContent = improving.name;
        if (improvingDetail && improving.change < 0) {
            improvingDetail.textContent = '\u2193' + Math.abs(improving.change).toFixed(0) + '% vs last period';
        }

        // Data freshness
        var freshnessEl = document.getElementById('data-freshness-text');
        if (freshnessEl) {
            freshnessEl.textContent = totalIncidents.toLocaleString() + ' incidents tracked \u00B7 Updated daily';
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadData);
    } else {
        loadData();
    }

    // Fix Leaflet map size when scrolled into view
    var mapSection = document.getElementById('map-section');
    if (mapSection && window.IntersectionObserver) {
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting && window.map) {
                    window.map.invalidateSize();
                }
            });
        }, { threshold: 0.1 });
        observer.observe(mapSection);
    }
})();
