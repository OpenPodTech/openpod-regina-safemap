"""
Scoring Weights — Configurable weights for neighbourhood scoring.

Adjust these to change how much each dimension matters in the overall score.
All weights should sum to 1.0.
"""

# ─── Overall Dimension Weights ────────────────────────────────────

SCORING_WEIGHTS = {
    "safety": 0.30,       # 30% — Crime is the #1 concern for newcomers
    "schools": 0.20,      # 20% — Critical for families
    "transit": 0.20,      # 20% — Essential without a car (newcomers often don't have one)
    "amenities": 0.20,    # 20% — Daily needs: grocery, healthcare, library
    "walkability": 0.10,  # 10% — Quality of life indicator
}

# ─── Safety Sub-Weights ───────────────────────────────────────────
# How much each factor contributes to the safety score

SAFETY_WEIGHTS = {
    "crime_density": 0.40,      # Raw incidents per area
    "crime_severity": 0.35,     # Weighted by violence level
    "crime_trend": 0.25,        # Year-over-year change (improving = bonus)
}

# ─── Crime Severity Multipliers ───────────────────────────────────
# Higher = worse (more points deducted from safety)

CRIME_SEVERITY_MULTIPLIER = {
    "Homicide": 10.0,
    "Sexual Assault": 9.0,
    "Robbery": 8.0,
    "Weapons Offences": 7.5,
    "Assault": 7.0,
    "Break and Enter - Residential": 6.0,
    "Break and Enter - Commercial": 5.0,
    "Theft of Motor Vehicle": 5.0,
    "Theft Over $5,000": 4.0,
    "Drug Offences": 3.5,
    "Fraud": 3.0,
    "Theft Under $5,000": 2.5,
    "Mischief": 2.0,
    "Other Criminal Code": 2.0,
}

# ─── Proximity Thresholds (metres) ───────────────────────────────
# Used to count "nearby" amenities for scoring

PROXIMITY = {
    "school_radius": 1000,          # Schools within 1km
    "transit_radius": 500,          # Bus stops within 500m
    "grocery_radius": 1000,         # Grocery within 1km
    "healthcare_radius": 1500,      # Healthcare within 1.5km
    "park_radius": 800,             # Park within 800m
    "community_radius": 1500,       # Library/community centre within 1.5km
}

# ─── Scoring Thresholds ──────────────────────────────────────────
# Number of nearby amenities needed for a "perfect" score in each category

IDEAL_COUNTS = {
    "schools": 3,           # 3+ schools nearby = 100 score
    "transit_stops": 8,     # 8+ bus stops nearby = 100 score
    "grocery": 2,           # 2+ grocery stores = 100 score
    "healthcare": 2,        # 2+ healthcare facilities = 100 score
    "parks": 3,             # 3+ parks nearby = 100 score
    "community": 1,         # 1+ library/community centre = 100 score
}

# ─── Grade Thresholds ────────────────────────────────────────────

GRADE_THRESHOLDS = [
    (90, "A+"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (0, "F"),
]


def get_grade(score: float) -> str:
    """Convert a numeric score (0-100) to a letter grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"
