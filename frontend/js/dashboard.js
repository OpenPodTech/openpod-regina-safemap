/**
 * Dashboard — Populates stats, trending, and comparison sections
 * Loads crime_stats.json and trends.json to power the hero dashboard.
 */
(function() {
    'use strict';

    var crimeStats = null;
    var trendsData = null;

    // Utility: animate number counting up
    function animateNumber(el, target, prefix, suffix) {
        prefix = prefix || '';
        suffix = suffix || '';
        var start = 0;
        var duration = 1200;
        var startTime = null;

        function step(ts) {
            if (!startTime) startTime = ts;
            var progress = Math.min((ts - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
            var current = Math.round(start + (target - start) * eased);
            el.textContent = prefix + current.toLocaleString() + suffix;
            if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
    }

    // Load both data files
    function loadData() {
        var statsPromise = fetch('data/processed/crime_stats.json')
            .then(function(r) { return r.ok ? r.json() : null; })
            .catch(function() { return null; });

        var trendsPromise = fetch('data/processed/trends.json')
            .then(function(r) { return r.ok ? r.json() : null; })
            .catch(function() { return null; });

        Promise.all([statsPromise, trendsPromise]).then(function(results) {
            crimeStats = results[0];
            trendsData = results[1];
            populateDashboard();
        });
    }

    function populateDashboard() {
        if (!crimeStats) return;

        // --- Stats Cards ---
        var totalIncidents = 0;
        var safest = { name: '--', count: Infinity };
        var hottest = { name: '--', count: 0 };
        var entries = [];

        for (var hood in crimeStats) {
            if (!crimeStats.hasOwnProperty(hood)) continue;
            var data = crimeStats[hood];
            var count = data.total_incidents || 0;
            totalIncidents += count;
            entries.push({ name: hood, count: count });

            if (count < safest.count && count > 0) {
                safest = { name: hood, count: count };
            }
            if (count > hottest.count) {
                hottest = { name: hood, count: count };
            }
        }

        // Animated total
        var totalEl = document.getElementById('stat-total');
        if (totalEl) animateNumber(totalEl, totalIncidents, '', '');

        // Period
        var periodEl = document.getElementById('stat-period');
        if (periodEl) {
            var sampleData = crimeStats[Object.keys(crimeStats)[0]];
            if (sampleData && sampleData.data_period) {
                periodEl.textContent = sampleData.data_period;
            }
        }

        // Safest
        var safestEl = document.getElementById('stat-safest');
        if (safestEl) safestEl.textContent = safest.name;
        var safestCountEl = document.getElementById('stat-safest-count');
        if (safestCountEl) safestCountEl.textContent = safest.count + ' incidents';

        // Hottest
        var hottestEl = document.getElementById('stat-hottest');
        if (hottestEl) hottestEl.textContent = hottest.name;
        var hottestCountEl = document.getElementById('stat-hottest-count');
        if (hottestCountEl) hottestCountEl.textContent = hottest.count + ' incidents';

        // City trend from trends.json
        if (trendsData && trendsData.city_summary) {
            var city = trendsData.city_summary;
            var trendEl = document.getElementById('stat-trend');
            var trendNoteEl = document.getElementById('stat-trend-note');

            if (city.yearly_totals) {
                var y2007 = city.yearly_totals['2007'] || 0;
                var y2018 = city.yearly_totals['2018'] || 0;
                if (y2007 > 0) {
                    var changePct = Math.round(((y2018 - y2007) / y2007) * 100);
                    var arrow = changePct < 0 ? '\u2193 ' : '\u2191 ';
                    if (trendEl) trendEl.textContent = arrow + Math.abs(changePct) + '%';
                    if (trendNoteEl) trendNoteEl.textContent = y2007.toLocaleString() + ' (2007) \u2192 ' + y2018.toLocaleString() + ' (2018)';

                    // Color the card
                    var trendCard = trendEl ? trendEl.closest('.stat-card') : null;
                    if (trendCard) {
                        trendCard.classList.add(changePct < 0 ? 'trend-good' : 'trend-bad');
                    }
                }
            }
        }

        // Data freshness
        var freshnessEl = document.getElementById('data-freshness-text');
        if (freshnessEl) {
            var sample = crimeStats[Object.keys(crimeStats)[0]];
            if (sample && sample.last_updated) {
                freshnessEl.textContent = 'Live data \u2022 ' + totalIncidents.toLocaleString() + ' incidents \u2022 Updated ' + sample.last_updated;
            }
        }

        // --- Trending Section ---
        populateTrending(entries);

        // --- Comparison Bars ---
        populateComparison(entries);
    }

    function populateTrending(entries) {
        var container = document.getElementById('trending-items');
        if (!container) return;

        // Find interesting insights
        var insights = [];

        // Top crime type city-wide
        var crimeTypeTotals = {};
        for (var hood in crimeStats) {
            var breakdown = crimeStats[hood].crime_breakdown || {};
            for (var crime in breakdown) {
                crimeTypeTotals[crime] = (crimeTypeTotals[crime] || 0) + breakdown[crime];
            }
        }
        var topCrime = Object.keys(crimeTypeTotals).sort(function(a, b) { return crimeTypeTotals[b] - crimeTypeTotals[a]; })[0];
        if (topCrime) {
            insights.push({
                icon: '\u26a0\ufe0f',
                text: topCrime + ' is the most common offence city-wide (' + crimeTypeTotals[topCrime].toLocaleString() + ' incidents)'
            });
        }

        // Neighbourhood with most B&E
        var beSorted = entries.filter(function(e) {
            return crimeStats[e.name] && crimeStats[e.name].crime_breakdown && crimeStats[e.name].crime_breakdown['Break & Enter'];
        }).sort(function(a, b) {
            return (crimeStats[b.name].crime_breakdown['Break & Enter'] || 0) - (crimeStats[a.name].crime_breakdown['Break & Enter'] || 0);
        });
        if (beSorted.length > 0) {
            var topBE = beSorted[0];
            insights.push({
                icon: '\ud83c\udfe0',
                text: 'Break & Enters highest in ' + topBE.name + ' (' + crimeStats[topBE.name].crime_breakdown['Break & Enter'] + ' incidents)'
            });
        }

        // Person crimes concentrated
        var personSorted = entries.filter(function(e) {
            return crimeStats[e.name] && crimeStats[e.name].person_crimes > 0;
        }).sort(function(a, b) {
            return (crimeStats[b.name].person_crimes || 0) - (crimeStats[a.name].person_crimes || 0);
        });
        if (personSorted.length > 0) {
            insights.push({
                icon: '\ud83d\udea8',
                text: personSorted[0].name + ' has the most person-crime incidents (' + crimeStats[personSorted[0].name].person_crimes + ')'
            });
        }

        // How many neighbourhoods have zero incidents
        var zeroCount = entries.filter(function(e) { return e.count === 0; }).length;
        if (zeroCount > 0) {
            insights.push({
                icon: '\u2728',
                text: zeroCount + ' neighbourhoods reported zero incidents this period'
            });
        }

        // Render
        container.innerHTML = '';
        insights.slice(0, 4).forEach(function(insight) {
            var div = document.createElement('div');
            div.className = 'trending-item';
            div.innerHTML = '<span class="trending-icon">' + insight.icon + '</span><span class="trending-text">' + insight.text + '</span>';
            container.appendChild(div);
        });
    }

    function populateComparison(entries) {
        // Sort and get top/bottom 5 (excluding zero)
        var nonZero = entries.filter(function(e) { return e.count > 0; });
        nonZero.sort(function(a, b) { return a.count - b.count; });

        var safest5 = nonZero.slice(0, 5);
        var hottest5 = nonZero.slice(-5).reverse();
        var maxCount = hottest5.length > 0 ? hottest5[0].count : 1;

        var safestContainer = document.getElementById('safest-bars');
        var hottestContainer = document.getElementById('hottest-bars');

        if (safestContainer) {
            safestContainer.innerHTML = '';
            safest5.forEach(function(item) {
                var pct = Math.max((item.count / maxCount) * 100, 3);
                var div = document.createElement('div');
                div.className = 'comp-bar-item';
                div.innerHTML = '<span class="comp-name">' + item.name + '</span>' +
                    '<div class="comp-bar-track"><div class="comp-bar-fill safe" style="width:' + pct + '%"></div></div>' +
                    '<span class="comp-count">' + item.count + '</span>';
                safestContainer.appendChild(div);
            });
        }

        if (hottestContainer) {
            hottestContainer.innerHTML = '';
            hottest5.forEach(function(item) {
                var pct = Math.max((item.count / maxCount) * 100, 3);
                var div = document.createElement('div');
                div.className = 'comp-bar-item';
                div.innerHTML = '<span class="comp-name">' + item.name + '</span>' +
                    '<div class="comp-bar-track"><div class="comp-bar-fill hot" style="width:' + pct + '%"></div></div>' +
                    '<span class="comp-count">' + item.count + '</span>';
                hottestContainer.appendChild(div);
            });
        }
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadData);
    } else {
        loadData();
    }

    // Fix Leaflet map size when scrolled into view (map is below fold)
    var mapSection = document.getElementById('map-section');
    if (mapSection && window.IntersectionObserver) {
        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting && window.map) {
                    window.map.invalidateSize();
                }
            });
        }, { threshold: 0.1 });
        observer.observe(mapSection);
    }
})();
