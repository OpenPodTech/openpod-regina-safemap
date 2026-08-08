/**
 * Regina SafeMap — Info Panel
 * Premium score ring, neighbourhood descriptions, and trend display.
 */

function showPanel(properties) {
    const panel = document.getElementById('info-panel');
    panel.classList.remove('panel-hidden');

    const name = properties.name || 'Unknown Neighbourhood';
    document.getElementById('panel-name').textContent = name;

    // Look up real crime data from global crimeStats
    const crimeData = window.crimeStats ? window.crimeStats[name] : null;
    const description = window.descriptions ? window.descriptions[name] : null;

    // Calculate or fetch scores
    const scores = properties.overall !== undefined ? properties : calculateQuickScore(properties, crimeData);
    updateScoreRing(scores);
    updateBreakdown(scores);
    updateFacts(properties, scores, crimeData);
    updateTrend(properties, crimeData);
    updateDescription(description);
}

function hidePanel() {
    const panel = document.getElementById('info-panel');
    panel.classList.add('panel-hidden');

    // Exit browse mode — restore header and welcome
    exitBrowseMode();

    if (selectedNeighbourhood) {
        selectedNeighbourhood.setStyle(CONFIG.NEIGHBOURHOOD_STYLE.default);
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
        facts.push(`${crimeData.latest_incidents.toLocaleString()} reported incidents (${crimeData.latest_year})`);
        if (crimeData.crime_breakdown) {
            const sorted = Object.entries(crimeData.crime_breakdown)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3);
            const topCrimes = sorted.map(([type, count]) => `${type}: ${count}`).join(', ');
            facts.push(`Top: ${topCrimes}`);
        }
    } else if (properties.total_crimes !== undefined && properties.total_crimes > 0) {
        facts.push(`${properties.total_crimes} reported incidents (latest year)`);
    }

    if (properties.schools_count !== undefined && properties.schools_count > 0) {
        facts.push(`${properties.schools_count} schools within 1km`);
    }
    if (properties.transit_stops !== undefined && properties.transit_stops > 0) {
        facts.push(`${properties.transit_stops} bus stops nearby`);
    }
    if (properties.parks_count !== undefined && properties.parks_count > 0) {
        facts.push(`${properties.parks_count} parks & green spaces`);
    }
    if (properties.grocery_count !== undefined && properties.grocery_count > 0) {
        facts.push(`${properties.grocery_count} grocery stores within 1km`);
    }

    if (facts.length === 0) {
        facts.push('Click to view detailed neighbourhood data');
        facts.push('Run data collection to populate scores');
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
        trendEl.textContent = `\u2193 Crime down ${Math.abs(trend).toFixed(1)}% vs last year \u2014 improving`;
        trendEl.className = 'trend-down';
    } else if (trend > 5) {
        trendEl.textContent = `\u2191 Crime up ${trend.toFixed(1)}% vs last year \u2014 declining`;
        trendEl.className = 'trend-up';
    } else {
        trendEl.textContent = '\u2192 Stable \u2014 no significant change';
        trendEl.className = 'trend-stable';
    }
}

function updateDescription(description) {
    let descEl = document.getElementById('panel-description');
    if (!descEl) {
        const panel = document.getElementById('panel-content');
        if (panel) {
            descEl = document.createElement('div');
            descEl.id = 'panel-description';
            descEl.className = 'panel-description';
            panel.appendChild(descEl);
        }
    }

    if (!descEl) return;

    if (description) {
        descEl.style.display = 'block';
        descEl.innerHTML = `
            ${description.vibe ? `<div class="desc-vibe">${description.vibe}</div>` : ''}
            ${description.description ? `<p class="desc-text">${description.description}</p>` : ''}
            ${description.best_for ? `<p class="desc-best"><span>Best for:</span> ${description.best_for}</p>` : ''}
            ${description.watch_out ? `<p class="desc-watch"><span>Watch out:</span> ${description.watch_out}</p>` : ''}
            ${description.avg_rent ? `<p class="desc-rent"><span>Avg rent:</span> <span class="desc-rent-value">${description.avg_rent}</span></p>` : ''}
        `;
    } else {
        descEl.style.display = 'none';
        descEl.innerHTML = '';
    }
}

function calculateQuickScore(properties, crimeData) {
    let safety = 65;
    if (crimeData && crimeData.latest_incidents !== undefined) {
        const maxCrime = 4751;
        const minCrime = 28;
        const incidents = crimeData.latest_incidents;
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
        if (score >= g.min) {
            return g;
        }
    }
    return CONFIG.GRADES[CONFIG.GRADES.length - 1];
}
