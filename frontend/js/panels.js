/**
 * Regina SafeMap — Info Panel
 * Displays neighbourhood details, scores, and trends.
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
    updateScoreDisplay(scores);
    updateBreakdown(scores);
    updateFacts(properties, scores, crimeData);
    updateTrend(properties, crimeData);
    updateDescription(description);
}

function hidePanel() {
    const panel = document.getElementById('info-panel');
    panel.classList.add('panel-hidden');

    if (selectedNeighbourhood) {
        selectedNeighbourhood.setStyle(CONFIG.NEIGHBOURHOOD_STYLE.default);
        selectedNeighbourhood = null;
    }
}

function updateScoreDisplay(scores) {
    const overall = scores.overall || 0;
    const gradeInfo = getGrade(overall);

    const numberEl = document.querySelector('.score-number');
    const gradeEl = document.querySelector('.score-grade');

    numberEl.textContent = overall;
    numberEl.style.color = gradeInfo.color;
    gradeEl.textContent = gradeInfo.grade;
    gradeEl.style.color = gradeInfo.color;
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

    // Use real crime data if available
    if (crimeData) {
        facts.push(`📊 ${crimeData.latest_incidents.toLocaleString()} reported incidents (${crimeData.latest_year})`);

        // Show top 3 crime types
        if (crimeData.crime_breakdown) {
            const sorted = Object.entries(crimeData.crime_breakdown)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3);
            const topCrimes = sorted.map(([type, count]) => `${type}: ${count}`).join(', ');
            facts.push(`🔍 Top crimes: ${topCrimes}`);
        }
    } else if (properties.total_crimes !== undefined && properties.total_crimes > 0) {
        facts.push(`📊 ${properties.total_crimes} reported incidents (latest year)`);
    }

    if (properties.schools_count !== undefined && properties.schools_count > 0) {
        facts.push(`🏫 ${properties.schools_count} schools within 1km`);
    }
    if (properties.transit_stops !== undefined && properties.transit_stops > 0) {
        facts.push(`🚌 ${properties.transit_stops} bus stops nearby`);
    }
    if (properties.parks_count !== undefined && properties.parks_count > 0) {
        facts.push(`🌳 ${properties.parks_count} parks & green spaces`);
    }
    if (properties.grocery_count !== undefined && properties.grocery_count > 0) {
        facts.push(`🛒 ${properties.grocery_count} grocery stores within 1km`);
    }

    // Add general facts if specific data not available
    if (facts.length === 0) {
        facts.push('📍 Click to view detailed neighbourhood data');
        facts.push('📊 Run data collection to populate scores');
    }

    facts.forEach((fact) => {
        const li = document.createElement('li');
        li.textContent = fact;
        factsList.appendChild(li);
    });
}

function updateTrend(properties, crimeData) {
    const trendEl = document.getElementById('trend-text');

    // Prefer crimeData from crime_stats.json
    const trend = crimeData ? crimeData.yoy_change_pct : (properties.crime_trend || 0);

    if (trend < -5) {
        trendEl.textContent = `↓ Crime down ${Math.abs(trend).toFixed(1)}% vs last year — improving`;
        trendEl.className = 'trend-down';
    } else if (trend > 5) {
        trendEl.textContent = `↑ Crime up ${trend.toFixed(1)}% vs last year — declining`;
        trendEl.className = 'trend-up';
    } else {
        trendEl.textContent = '→ Stable — no significant change';
        trendEl.className = 'trend-stable';
    }
}

function updateDescription(description) {
    // Find or create description container
    let descEl = document.getElementById('panel-description');
    if (!descEl) {
        // Create description section if it doesn't exist in HTML
        const panel = document.getElementById('info-panel');
        const factsSection = document.getElementById('panel-facts');
        if (factsSection && panel) {
            descEl = document.createElement('div');
            descEl.id = 'panel-description';
            descEl.className = 'panel-description';
            factsSection.parentNode.insertBefore(descEl, factsSection.nextSibling);
        }
    }

    if (!descEl) return;

    if (description) {
        descEl.style.display = 'block';
        descEl.innerHTML = `
            <div class="desc-vibe"><strong>${description.vibe || ''}</strong></div>
            <p class="desc-text">${description.description || ''}</p>
            ${description.best_for ? `<p class="desc-best"><span>Best for:</span> ${description.best_for}</p>` : ''}
            ${description.watch_out ? `<p class="desc-watch"><span>Watch out:</span> ${description.watch_out}</p>` : ''}
            ${description.avg_rent ? `<p class="desc-rent"><span>Avg rent:</span> ${description.avg_rent}</p>` : ''}
        `;
    } else {
        descEl.style.display = 'none';
        descEl.innerHTML = '';
    }
}

function calculateQuickScore(properties, crimeData) {
    // If we have crime data, compute a reasonable safety score
    let safety = 65;
    if (crimeData && crimeData.latest_incidents !== undefined) {
        // Quick normalization: North Central is ~4751 (worst), Whitmore Park is ~164 (best)
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
