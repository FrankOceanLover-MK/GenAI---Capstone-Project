"""Deterministic filtering and scoring for local car listings."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# CHANGE: Import the new fetcher instead of SAMPLE_LISTINGS
from external_apis import fetch_active_listings


@dataclass
class ScoreBreakdown:
    price: float
    mileage: float
    distance: float
    economy: float
    safety: float

    def total(self) -> float:
        # Simple weighted sum; weights sum to 1.0
        return round(
            0.32 * self.price
            + 0.2 * self.mileage
            + 0.18 * self.distance
            + 0.2 * self.economy
            + 0.1 * self.safety,
            3,
        )


@dataclass
class SearchCriteria:
    budget: Optional[float] = None
    max_distance: Optional[float] = None
    body_style: Optional[str] = None
    fuel_type: Optional[str] = None


@dataclass
class ListingWithScore:
    listing: Dict[str, Any]
    breakdown: ScoreBreakdown

    @property
    def total_score(self) -> float:
        return self.breakdown.total()


# ----------------------------------------------------------------------------
# Scoring helpers (Restored)
# ----------------------------------------------------------------------------

def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def _price_score(price: Optional[float], budget: Optional[float]) -> float:
    if price is None:
        return 0.4  # unknown price: downgrade confidence
    if budget is None:
        return 0.6  # budget not provided: neutral-ish
    # Score is 1.0 when price <= budget, decays as it exceeds budget
    if price <= budget:
        return 1.0
    # allow up to 20% over budget but penalize sharply
    return _clamp(1 - ((price - budget) / (budget * 0.2)))


def _mileage_score(mileage: Optional[float]) -> float:
    if mileage is None:
        return 0.5
    # 0-30k miles is great, 30k-90k tapers, >120k poor
    if mileage <= 30000:
        return 1.0
    if mileage <= 90000:
        return _clamp(1 - (mileage - 30000) / 60000)
    if mileage <= 120000:
        return 0.2
    return 0.05


def _distance_score(distance: Optional[float], max_distance: Optional[float]) -> float:
    if distance is None:
        return 0.4
    if max_distance is None:
        # still prefer closer cars
        return _clamp(1 - (distance / 200))
    if distance <= max_distance:
        return 1.0
    # Past the limit, decay to 0 at 2x the limit
    return _clamp(1 - ((distance - max_distance) / max(max_distance, 1)))


def _economy_score(city_mpg: Optional[float], highway_mpg: Optional[float]) -> float:
    mpg_values = [v for v in (city_mpg, highway_mpg) if v]
    if not mpg_values:
        return 0.5
    avg_mpg = sum(mpg_values) / len(mpg_values)
    # 50+ mpg is excellent, 25 mpg is average; clamp accordingly
    return _clamp((avg_mpg - 20) / 30)


def _safety_score(rating: Optional[float]) -> float:
    if rating is None:
        return 0.6
    return _clamp(rating / 5)


def score_listing(listing: Dict[str, Any], criteria: SearchCriteria) -> ListingWithScore:
    breakdown = ScoreBreakdown(
        price=_price_score(listing.get("price"), criteria.budget),
        mileage=_mileage_score(listing.get("mileage")),
        distance=_distance_score(listing.get("distance_miles"), criteria.max_distance),
        economy=_economy_score(listing.get("city_mpg"), listing.get("highway_mpg")),
        safety=_safety_score(listing.get("safety_rating")),
    )
    return ListingWithScore(listing=listing, breakdown=breakdown)


# ----------------------------------------------------------------------------
# Search pipeline
# ----------------------------------------------------------------------------

def filter_listings(criteria: SearchCriteria) -> List[Dict[str, Any]]:
    """
    Deprecated: We now rely on the API to filter, but we keep this
    if we need to do any secondary post-filtering locally.
    """
    # This is handled mostly by the API now, but we can leave it empty or 
    # reuse it for logic the API doesn't support.
    return [] 


def search(criteria: SearchCriteria, top_k: int = 5) -> List[ListingWithScore]:
    """Filter, score, and rank listings."""
    
    # 1. Fetch REAL listings from Auto.dev
    candidates = fetch_active_listings(
        budget=criteria.budget,
        min_year=2015, # Optional default to keep results relevant
        body_style=criteria.body_style,
        limit=20
    )

    # 2. Score and rank them
    scored = [score_listing(item, criteria) for item in candidates]
    scored.sort(key=lambda s: s.total_score, reverse=True)
    return scored[:top_k]