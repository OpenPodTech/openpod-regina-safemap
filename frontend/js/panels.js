/**
 * Regina SafeMap — Info Panel
 * Displays neighbourhood details, scores, and trends.
 */

function showPanel(properties) {
    const panel = document.getElementById('info-panel');
    panel.classList.remove('panel-hidden');

    const name = properties.name || 'Unknown Neighbourhood';
    document.getElementById('panel-name').textContent = name;

    // Calculate or fetch scores
    const scores = properties.scores || calculateQuickScore(properties);
    updateScoreDisplay(scores);
    updateBreakdown(scores);
    updateFacts(properties, scores);
    updateTrend(properties);
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
        const valueEl = row.closest('.score-row').querySelector('.score-value');

        row.style.width = `${value}%`;
        valueEl.textContent = value;
    });
}

function updateFacts(properties, scores) {
    const factsList = document.getElementById('panel-facts');
    factsList.innerHTML = '';

    const facts = [];

    if (properties.total_crimes !== undefined) {
        facts.push(`📊 ${properties.total_crimes} reported incidents (latest year)`);
    }
    if (properties.schools_count !== undefined) {
        facts.push(`🏫 ${properties.schools_count} schools within 1km`);
    }
    if (properties.transit_stops !== undefined) {
        facts.push(`🚌 ${properties.transit_stops} bus stops nearby`);
    }
    if (properties.parks_count !== undefined) {
        facts.push(`🌳 ${properties.parks_count} parks & green spaces`);
    }
    if (properties.grocery_count !== undefined) {
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

function updateTrend(properties) {
    const trendEl = document.getElementById('trend-text');
    const trend = properties.crime_trend || 0;

    if (trend < -5) {
        trendEl.textContent = `↓ Crime down ${Math.abs(trend)}% vs last year — improving`;
        trendEl.className = 'trend-down';
    } else if (trend > 5) {
        trendEl.textContent = `↑ Crime up ${trend}% vs last year — declining`;
        trendEl.className = 'trend-up';
    } else {
        trendEl.textContent = '→ Stable — no significant change';
        trendEl.className = 'trend-stable';
    }
}

function calculateQuickScore(properties) {
    // Simple score estimation when backend scores aren't available
    // This will be replaced by the actual scoring engine
    return {
        overall: properties.overall_score || 65,
        safety: properties.safety_score || 60,
        schools: properties.schools_score || 70,
        transit: properties.transit_score || 65,
        amenities: properties.amenities_score || 68,
        walkability: properties.walkability_score || 55,
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
