"""
Neighbourhood Scoring Calculator

Computes a 0-100 score for each neighbourhood across 5 dimensions:
- Safety (30%): Based on crime density, severity, and year-over-year trend
- Schools (20%): Based on number and proximity of schools
- Transit (20%): Based on bus stop density and coverage
- Amenities (20%): Grocery, healthcare, libraries, community centres
- Walkability (10%): Parks + transit + amenity density combined

Each dimension is scored 0-100, then weighted to produce an overall score.
"""

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .weights import (
    SCORING_WEIGHTS,
    SAFETY_WEIGHTS,
    CRIME_SEVERITY_MULTIPLIER,
    PROXIMITY,
    IDEAL_COUNTS,
    get_grade,
)

logger = logging.getLogger(__name__)


@dataclass
class NeighbourhoodScore:
    """Complete score for a single neighbourhood."""
    name: str
    overall: int = 0
    grade: str = "—"
    safety: int = 0
    schools: int = 0
    transit: int = 0
    amenities: int = 0
    walkability: int = 0

    # Supporting data
    total_crimes: int = 0
    crime_trend: float = 0.0  # % change year-over-year (negative = improving)
    schools_count: int = 0
    transit_stops: int = 0
    grocery_count: int = 0
    healthcare_count: int = 0
    parks_count: int = 0
    community_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "overall": self.overall,
            "grade": self.grade,
            "safety": self.safety,
            "schools": self.schools,
            "transit": self.transit,
            "amenities": self.amenities,
            "walkability": self.walkability,
            "total_crimes": self.total_crimes,
            "crime_trend": self.crime_trend,
            "schools_count": self.schools_count,
            "transit_stops": self.transit_stops,
            "grocery_count": self.grocery_count,
            "healthcare_count": self.healthcare_count,
            "parks_count": self.parks_count,
            "community_count": self.community_count,
        }


class NeighbourhoodScorer:
    """
    Calculates livability scores for all Regina neighbourhoods.

    Reads processed GeoJSON data and crime_stats.json to produce differentiated scores.
    """

    def __init__(self, data_dir: str = "data/processed"):
        self.data_dir = Path(data_dir)
        self.neighbourhoods = []
        self.crimes = []
        self.crime_stats = {}  # Direct from crime_stats.json
        self.schools = []
        self.transit_stops = []
        self.amenities = []
        self.parks = []

    def load_data(self):
        """Load all processed GeoJSON files and crime_stats.json."""
        self.neighbourhoods = self._load_geojson("neighbourhoods.geojson")
        self.crimes = self._load_geojson("crimes.geojson")
        self.schools = self._load_geojson("schools.geojson")
        self.transit_stops = self._load_geojson("transit_stops.geojson")
        self.amenities = self._load_geojson("amenities.geojson")
        self.parks = self._load_geojson("parks.geojson")

        # Load crime_stats.json directly — this is the authoritative source
        crime_stats_path = self.data_dir / "crime_stats.json"
        if crime_stats_path.exists():
            self.crime_stats = json.loads(crime_stats_path.read_text())
            logger.info(f"Loaded crime_stats.json with {len(self.crime_stats)} neighbourhoods")
        else:
            logger.warning("crime_stats.json not found — safety scores will use defaults")
            self.crime_stats = {}

        logger.info(
            f"Loaded: {len(self.neighbourhoods)} neighbourhoods, "
            f"{len(self.crimes)} crimes, {len(self.schools)} schools, "
            f"{len(self.transit_stops)} transit stops, "
            f"{len(self.amenities)} amenities, {len(self.parks)} parks"
        )

    def score_all(self) -> list[NeighbourhoodScore]:
        """Calculate scores for all neighbourhoods."""
        self.load_data()

        scores = []

        # Build crime stats lookup (case-insensitive)
        crime_lookup = {k.lower(): v for k, v in self.crime_stats.items()}

        # Calculate min/max for normalization from crime_stats.json
        if crime_lookup:
            all_incidents = [v["latest_incidents"] for v in crime_lookup.values() if v.get("latest_incidents")]
            max_incidents = max(all_incidents) if all_incidents else 1
            min_incidents = min(all_incidents) if all_incidents else 0
        else:
            max_incidents = 1
            min_incidents = 0

        for neighbourhood in self.neighbourhoods:
            props = neighbourhood.get("properties", {})
            name = props.get("name", "Unknown")
            centroid = self._get_centroid(neighbourhood)

            if not centroid:
                continue

            score = NeighbourhoodScore(name=name)

            # Calculate safety from crime_stats.json directly
            score.safety, score.total_crimes, score.crime_trend = self._score_safety(
                name, crime_lookup, max_incidents, min_incidents
            )
            score.schools, score.schools_count = self._score_schools(centroid)
            score.transit, score.transit_stops = self._score_transit(centroid)
            score.amenities, score.grocery_count, score.healthcare_count, score.community_count = (
                self._score_amenities(centroid)
            )
            score.walkability, score.parks_count = self._score_walkability(centroid, score)

            # Calculate overall weighted score
            score.overall = round(
                score.safety * SCORING_WEIGHTS["safety"]
                + score.schools * SCORING_WEIGHTS["schools"]
                + score.transit * SCORING_WEIGHTS["transit"]
                + score.amenities * SCORING_WEIGHTS["amenities"]
                + score.walkability * SCORING_WEIGHTS["walkability"]
            )
            score.grade = get_grade(score.overall)

            scores.append(score)

        # Sort by overall score (best first)
        scores.sort(key=lambda s: s.overall, reverse=True)
        logger.info(f"Scored {len(scores)} neighbourhoods")

        return scores

    def score_and_save(self) -> list[NeighbourhoodScore]:
        """Score all neighbourhoods and save results."""
        scores = self.score_all()

        # Save as JSON
        output = {
            "metadata": {
                "total_neighbourhoods": len(scores),
                "scoring_weights": SCORING_WEIGHTS,
            },
            "scores": [s.to_dict() for s in scores],
        }

        output_path = self.data_dir / "scores.json"
        output_path.write_text(json.dumps(output, indent=2))
        logger.info(f"Saved scores to {output_path}")

        # Also enrich the neighbourhoods GeoJSON with scores
        self._enrich_geojson(scores)

        return scores

    # ─── Scoring Methods ──────────────────────────────────────────────

    def _score_safety(
        self, name: str, crime_lookup: dict, max_incidents: int, min_incidents: int
    ) -> tuple[int, int, float]:
        """
        Score safety 0-100 based on crime_stats.json data directly.
        
        Higher score = SAFER (less crime).
        Uses min-max normalization across all neighbourhoods.
        """
        # Look up this neighbourhood in crime_stats (case-insensitive)
        stats = crime_lookup.get(name.lower())

        if not stats:
            # Try fuzzy match — strip common suffixes/prefixes
            for key, val in crime_lookup.items():
                if name.lower() in key or key in name.lower():
                    stats = val
                    break

        if not stats:
            # No crime data — assign middle score
            return 50, 0, 0.0

        total_crimes = stats.get("latest_incidents", 0)
        trend_pct = stats.get("yoy_change_pct", 0.0)
        severity_score_raw = stats.get("weighted_severity_score", 0)

        # Safety score based on relative crime position
        # score = 100 - ((this_neighbourhood_incidents / max_incidents) * 100)
        # This gives lowest-crime neighbourhood ~96-100, highest ~0-5
        incident_range = max(max_incidents - min_incidents, 1)
        base_safety = 100 - ((total_crimes - min_incidents) / incident_range * 100)

        # Apply trend bonus/penalty (up to +/-10 points)
        trend_bonus = 0
        if trend_pct < -10:
            trend_bonus = 10  # Strong improvement
        elif trend_pct < -5:
            trend_bonus = 5   # Moderate improvement
        elif trend_pct > 10:
            trend_bonus = -8  # Getting worse
        elif trend_pct > 5:
            trend_bonus = -4  # Slightly worse

        safety = round(base_safety + trend_bonus)
        safety = max(0, min(100, safety))

        return safety, total_crimes, round(trend_pct, 1)

    def _score_schools(self, centroid: tuple) -> tuple[int, int]:
        """Score schools 0-100 based on proximity and count."""
        radius = PROXIMITY["school_radius"] / 111000  # Convert m to ~degrees
        nearby = self._count_nearby(self.schools, centroid, radius)

        # Score: proportion of ideal count, capped at 100
        ideal = IDEAL_COUNTS["schools"]
        score = min(100, round((nearby / ideal) * 100)) if ideal > 0 else 0

        return score, nearby

    def _score_transit(self, centroid: tuple) -> tuple[int, int]:
        """Score transit 0-100 based on bus stop density."""
        radius = PROXIMITY["transit_radius"] / 111000
        nearby = self._count_nearby(self.transit_stops, centroid, radius)

        ideal = IDEAL_COUNTS["transit_stops"]
        score = min(100, round((nearby / ideal) * 100)) if ideal > 0 else 0

        return score, nearby

    def _score_amenities(self, centroid: tuple) -> tuple[int, int, int, int]:
        """Score amenities based on grocery, healthcare, and community facilities."""
        grocery_radius = PROXIMITY["grocery_radius"] / 111000
        healthcare_radius = PROXIMITY["healthcare_radius"] / 111000
        community_radius = PROXIMITY["community_radius"] / 111000

        # Count by category
        grocery_nearby = self._count_nearby_by_category(
            self.amenities, centroid, grocery_radius, "grocery"
        )
        healthcare_nearby = self._count_nearby_by_category(
            self.amenities, centroid, healthcare_radius, "healthcare"
        )
        community_nearby = self._count_nearby_by_category(
            self.amenities, centroid, community_radius, "community"
        )

        # Sub-scores
        grocery_score = min(100, round((grocery_nearby / IDEAL_COUNTS["grocery"]) * 100))
        healthcare_score = min(100, round((healthcare_nearby / IDEAL_COUNTS["healthcare"]) * 100))
        community_score = min(100, round((community_nearby / IDEAL_COUNTS["community"]) * 100))

        # Combined amenity score (equal weight to each sub-category)
        score = round((grocery_score + healthcare_score + community_score) / 3)

        return score, grocery_nearby, healthcare_nearby, community_nearby

    def _score_walkability(self, centroid: tuple, partial_score: NeighbourhoodScore) -> tuple[int, int]:
        """
        Score walkability as a composite of parks + transit + amenity proximity.
        
        Walkability is a "meta" dimension — areas with lots of things nearby
        are inherently more walkable.
        """
        park_radius = PROXIMITY["park_radius"] / 111000
        parks_nearby = self._count_nearby(self.parks, centroid, park_radius)

        park_score = min(100, round((parks_nearby / IDEAL_COUNTS["parks"]) * 100))

        # Walkability = 40% parks + 30% transit + 30% amenities
        score = round(
            park_score * 0.4
            + partial_score.transit * 0.3
            + partial_score.amenities * 0.3
        )

        return score, parks_nearby

    # ─── Helpers ──────────────────────────────────────────────────────

    def _load_geojson(self, filename: str) -> list[dict]:
        """Load features from a GeoJSON file."""
        path = self.data_dir / filename
        if not path.exists():
            logger.warning(f"  Data file not found: {path}")
            return []

        data = json.loads(path.read_text())
        return data.get("features", [])

    def _get_centroid(self, feature: dict) -> Optional[tuple]:
        """Get centroid (lat, lon) from a GeoJSON feature."""
        geom = feature.get("geometry", {})
        geom_type = geom.get("type", "")

        if geom_type == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                return (coords[1], coords[0])  # GeoJSON is [lon, lat]

        elif geom_type == "Polygon":
            coords = geom.get("coordinates", [[]])[0]
            if coords:
                avg_lon = sum(c[0] for c in coords) / len(coords)
                avg_lat = sum(c[1] for c in coords) / len(coords)
                return (avg_lat, avg_lon)

        elif geom_type == "MultiPolygon":
            all_coords = []
            for polygon in geom.get("coordinates", []):
                all_coords.extend(polygon[0])
            if all_coords:
                avg_lon = sum(c[0] for c in all_coords) / len(all_coords)
                avg_lat = sum(c[1] for c in all_coords) / len(all_coords)
                return (avg_lat, avg_lon)

        return None

    def _feature_coords(self, feature: dict) -> tuple:
        """Get (lat, lon) from a point feature."""
        coords = feature.get("geometry", {}).get("coordinates", [0, 0])
        return (coords[1], coords[0])

    def _distance(self, point1: tuple, point2: tuple) -> float:
        """Simple Euclidean distance in degrees (approximate for nearby points)."""
        return math.sqrt(
            (point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2
        )

    def _count_nearby(self, features: list[dict], centroid: tuple, radius_deg: float) -> int:
        """Count features within radius of centroid."""
        count = 0
        for feature in features:
            coords = self._feature_coords(feature)
            if self._distance(centroid, coords) <= radius_deg:
                count += 1
        return count

    def _count_nearby_by_category(
        self, features: list[dict], centroid: tuple, radius_deg: float, category: str
    ) -> int:
        """Count features of a specific category within radius."""
        count = 0
        for feature in features:
            if feature.get("properties", {}).get("category") == category:
                coords = self._feature_coords(feature)
                if self._distance(centroid, coords) <= radius_deg:
                    count += 1
        return count



    def _enrich_geojson(self, scores: list[NeighbourhoodScore]):
        """Add scores to the neighbourhoods GeoJSON for frontend consumption."""
        # Load original GeoJSON
        path = self.data_dir / "neighbourhoods.geojson"
        if not path.exists():
            return

        data = json.loads(path.read_text())

        # Create lookup by name
        score_lookup = {s.name.lower(): s for s in scores}

        # Enrich each feature
        for feature in data.get("features", []):
            name = feature.get("properties", {}).get("name", "")
            score = score_lookup.get(name.lower())
            if score:
                feature["properties"].update(score.to_dict())

        # Write enriched version
        enriched_path = self.data_dir / "neighbourhoods_scored.geojson"
        enriched_path.write_text(json.dumps(data, indent=2))
        logger.info(f"  Enriched GeoJSON saved to {enriched_path}")


# ─── CLI Entry Point ──────────────────────────────────────────────

def main():
    """Run scoring standalone."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    scorer = NeighbourhoodScorer()
    scores = scorer.score_and_save()

    # Print summary
    print("\n" + "=" * 60)
    print("  REGINA SAFEMAP — Neighbourhood Scores")
    print("=" * 60)
    print(f"\n{'Neighbourhood':<25} {'Score':>5} {'Grade':>5} {'Safety':>6} {'Schools':>7} {'Transit':>7}")
    print("-" * 70)

    for score in scores[:20]:  # Top 20
        print(
            f"{score.name:<25} {score.overall:>5} {score.grade:>5} "
            f"{score.safety:>6} {score.schools:>7} {score.transit:>7}"
        )

    if len(scores) > 20:
        print(f"\n... and {len(scores) - 20} more neighbourhoods")

    print(f"\nBest: {scores[0].name} ({scores[0].overall}/100 — {scores[0].grade})")
    if len(scores) > 1:
        print(f"Worst: {scores[-1].name} ({scores[-1].overall}/100 — {scores[-1].grade})")


if __name__ == "__main__":
    main()
