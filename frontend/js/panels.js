/**
 * Regina SafeMap — Info Panel
 * Clean side panel with score, description, and facts.
 */

function showPanel(properties) {
    const panel = document.getElementById('info-panel');
    panel.classList.remove('panel-hidden');
    panel.classList.add('panel-visible');

    const name = properties.name || 'Unknown Neighbourhood';
    document.getElementById('panel-name').textContent = name;

    // Look up real crime data and descriptions
    const crimeData = window.crimeStats ? window.crimeStats[name] : null;
    const description = window.descriptions ? window.descriptions[name] : null;

    // Calculate scores
    const scores = properties.overall !== undefined ? properties : calculateQuickScore(properties, crimeData);
    updateScoreRing(scores);
    updateBreakdown(scores);
    updateFacts(properties, scores, crimeData);
    updateTrend(properties, crimeData);
    updateDescription(description);
}

function hidePanel() {
    const panel = document.getElementById('info-panel');
    panel.classList.remove('panel-visible');
    panel.classList.add('panel-hidden');

    if (selectedNeighbourhood) {
        const feature = selectedNeighbourhood.feature;
        selectedNeighbourhood.setStyle(getNeighbourhoodStyle(feature));
        selectedNeighbourhood = null;
    }
}

function updateScoreRing(scores) {
    const overall = scores.overall || 0;
    const gradeInfo = getGrade(overall);
    const ring = document.getElementById('score-ring');
    const ringFill = ring.querySelector('.ring-fill');
    const valueEl = ring.querySelector('.score-value');
    const gradeEl = ring.querySelector('.score-grade');

    // Calculate stroke-dashoffset (283 = full circumference of r=45)
    const circumference = 283;
    const offset = circumference - (circumference * overall / 100);
    ringFill.style.strokeDashoffset = offset;

    // Set score color class
    ring.className = 'score-ring';
    if (overall >= 90) {
        ring.classList.add('score-excellent');
    } else if (overall >= 70) {
        ring.classList.add('score-good');
    } else if (overall >= 50) {
        ring.classList.add('score-fair');
    } else {
        ring.classList.add('score-poor');
    }

    valueEl.textContent = overall;
    gradeEl.textContent = gradeInfo.grade;
}

function updateBreakdown(scores) {
    const dimensions = ['safety', 'schools', 'transit', 'amenities', 'walkability'];

    dimensions.forEach((dim) => {
        const value = scores[dim] || 0;
        const row = document.querySelector(`.score-fill.${dim}`);
        if (!row) return;
        const valueEl = row.closest('.score-row').querySelector('.score-value');

        row.style.width = `${value}%`;
        if (valueEl) valueEl.textContent = value;
    });
}

function updateFacts(properties, scores, crimeData) {
    const factsList = document.getElementById('panel-facts');
    factsList.innerHTML = '';

    const facts = [];

    if (crimeData) {
        const count = crimeData.total_incidents || crimeData.latest_incidents || 0;
        if (count > 0) {
            facts.push(`${count.toLocaleString()} incidents this period`);
        }
        if (crimeData.crime_breakdown) {
            const sorted = Object.entries(crimeData.crime_breakdown)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3);
            const topCrimes = sorted.map(([type, count]) => `${type} (${count})`).join(', ');
            if (topCrimes) facts.push(`Top: ${topCrimes}`);
        }
    } else if (properties.total_crimes !== undefined && properties.total_crimes > 0) {
        facts.push(`${properties.total_crimes} reported incidents`);
    }

    if (properties.schools_count > 0) {
        facts.push(`${properties.schools_count} schools nearby`);
    }
    if (properties.transit_stops > 0) {
        facts.push(`${properties.transit_stops} bus stops`);
    }
    if (properties.parks_count > 0) {
        facts.push(`${properties.parks_count} parks & green spaces`);
    }

    if (facts.length === 0) {
        facts.push('Click a neighbourhood on the map for details');
    }

    facts.forEach((fact) => {
        const li = document.createElement('li');
        li.textContent = fact;
        factsList.appendChild(li);
    });
}

function updateTrend(properties, crimeData) {
    const trendEl = document.getElementById('trend-text');
    const trend = crimeData ? crimeData.yoy_change_pct : (properties.crime_trend || 0);

    if (trend < -5) {
        trendEl.textContent = `\u2193 Down ${Math.abs(trend).toFixed(0)}% vs last period \u2014 improving`;
        trendEl.className = 'trend-down';
    } else if (trend > 5) {
        trendEl.textContent = `\u2191 Up ${trend.toFixed(0)}% vs last period`;
        trendEl.className = 'trend-up';
    } else {
        trendEl.textContent = '\u2192 Stable \u2014 no significant change';
        trendEl.className = 'trend-stable';
    }
}

function updateDescription(description) {
    const descEl = document.getElementById('panel-description');
    if (!descEl) return;

    if (description) {
        descEl.style.display = 'block';
        let html = '';
        if (description.vibe) html += `<div class="desc-vibe">${description.vibe}</div>`;
        if (description.description) html += `<p class="desc-text">${description.description}</p>`;
        if (description.best_for) html += `<p class="desc-best"><span>Best for:</span> ${description.best_for}</p>`;
        if (description.avg_rent) html += `<p class="desc-rent"><span>Rent:</span> ${description.avg_rent}</p>`;
        if (description.watch_out) html += `<p class="desc-watch"><span>Note:</span> ${description.watch_out}</p>`;
        descEl.innerHTML = html;
    } else {
        descEl.style.display = 'none';
        descEl.innerHTML = '';
    }
}

function calculateQuickScore(properties, crimeData) {
    let safety = 65;
    if (crimeData && (crimeData.total_incidents || crimeData.latest_incidents)) {
        const maxCrime = 4751;
        const minCrime = 28;
        const incidents = crimeData.total_incidents || crimeData.latest_incidents;
        safety = Math.round(100 - ((incidents - minCrime) / (maxCrime - minCrime)) * 100);
        safety = Math.max(0, Math.min(100, safety));
    }

    return {
        overall: properties.overall || Math.round(safety * 0.3 + 65 * 0.7),
        safety: properties.safety || safety,
        schools: properties.schools || 0,
        transit: properties.transit || 0,
        amenities: properties.amenities || 0,
        walkability: properties.walkability || 0,
    };
}

function getGrade(score) {
    for (const g of CONFIG.GRADES) {
        if (score >= g.min) return g;
    }
    return CONFIG.GRADES[CONFIG.GRADES.length - 1];
}
