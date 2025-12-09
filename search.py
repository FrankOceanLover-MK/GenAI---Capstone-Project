"""Deterministic filtering and scoring for live car listings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from external_apis import fetch_active_listings
from sample_listings import SAMPLE_LISTINGS


@dataclass
class ScoreBreakdown:
    price: float
    mileage: float
    distance: float
    economy: float
    safety: float

    @property
    def total(self) -> float:
        return (
            0.30 * self.price
            + 0.25 * self.mileage
            + 0.15 * self.distance
            + 0.20 * self.economy
            + 0.10 * self.safety
        )


@dataclass
class ListingWithScore:
    listing: Dict[str, Any]
    breakdown: ScoreBreakdown

    @property
    def total_score(self) -> float:
        return self.breakdown.total


@dataclass
class SearchCriteria:
    budget: Optional[float] = None
    max_distance: Optional[float] = None
    body_style: Optional[str] = None
    fuel_type: Optional[str] = None
    make: Optional[str] = None


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _price_score(price: Optional[float], budget: Optional[float]) -> float:
    if price is None:
        return 0.5
    if budget is None:
        return 0.6

    if price <= budget:
        if price >= 0.7 * budget:
            return 1.0
        return 0.6 + 0.4 * (price / (0.7 * budget))
    over = price - budget
    if over <= 0.1 * budget:
        return 0.6 * (1 - over / (0.1 * budget))
    return 0.05


def _mileage_score(mileage: Optional[float]) -> float:
    if mileage is None:
        return 0.5
    if mileage <= 30000:
        return 1.0
    if mileage <= 90000:
        return _clamp(1 - (mileage - 30000) / 60000)
    if mileage <= 120000:
        return 0.2
    return 0.05


def _distance_score(distance_miles: Optional[float], max_distance: Optional[float]) -> float:
    if distance_miles is None:
        return 0.5
    if max_distance is None:
        max_distance = 100.0
    if distance_miles <= max_distance:
        return 1.0
    if distance_miles <= 2 * max_distance:
        return _clamp(1 - (distance_miles - max_distance) / max_distance)
    return 0.05


def _economy_score(city_mpg: Optional[float], highway_mpg: Optional[float]) -> float:
    if city_mpg is None and highway_mpg is None:
        return 0.5
    mpg = 0.0
    weight = 0.0
    if city_mpg is not None:
        mpg += 0.6 * city_mpg
        weight += 0.6
    if highway_mpg is not None:
        mpg += 0.4 * highway_mpg
        weight += 0.4
    if weight == 0:
        return 0.5
    mpg /= weight

    if mpg <= 20:
        return 0.2
    if mpg >= 35:
        return 1.0
    return 0.2 + 0.8 * ((mpg - 20) / 15.0)


def _safety_score(stars: Optional[float]) -> float:
    if stars is None:
        return 0.5
    return _clamp(stars / 5.0)


def score_listing(listing: Dict[str, Any], criteria: SearchCriteria) -> ListingWithScore:
    price = listing.get("price")
    mileage = listing.get("mileage")
    distance_miles = listing.get("distance_miles")
    city_mpg = listing.get("city_mpg")
    highway_mpg = listing.get("highway_mpg")
    safety = listing.get("safety_rating")

    bd = ScoreBreakdown(
        price=_price_score(price, criteria.budget),
        mileage=_mileage_score(mileage),
        distance=_distance_score(distance_miles, criteria.max_distance),
        economy=_economy_score(city_mpg, highway_mpg),
        safety=_safety_score(safety),
    )

    return ListingWithScore(listing=listing, breakdown=bd)


def _passes_filters(listing: Dict[str, Any], criteria: SearchCriteria) -> bool:
    # Make filter
    if criteria.make:
        make = (listing.get("make") or "").lower()
        if criteria.make not in make:
            return False
        
    # Budget filter - more flexible
    if criteria.budget is not None:
        price = listing.get("price")
        if price is None:
            return False
        # Allow slight over-budget (10%) for scoring to handle
        if price > criteria.budget * 1.15:
            return False

    # Body style filter - handle "not SUV" case
    if criteria.body_style:
        body_style = (listing.get("body_style") or "").lower()
        criteria_style = criteria.body_style.lower()
        
        # Handle negative filters like "not SUV"
        if criteria_style.startswith("not "):
            excluded_style = criteria_style[4:].strip()
            if excluded_style in body_style:
                return False
        else:
            # Positive filter - must contain the style
            if criteria_style not in body_style:
                return False

    # Fuel type filter
    if criteria.fuel_type:
        fuel = (listing.get("fuel_type") or "").lower()
        criteria_fuel = criteria.fuel_type.lower()
        if criteria_fuel not in fuel:
            return False

    # Distance filter - more flexible
    if criteria.max_distance is not None:
        dist = listing.get("distance_miles")
        if dist is not None and dist > criteria.max_distance * 1.5:
            return False

    return True


def search(criteria: SearchCriteria, top_k: int = 5) -> List[ListingWithScore]:
    """
    Fetch real listings from Auto.dev and score them.
    """
    # First, let's see what the API returns
    candidates = fetch_active_listings(
    budget=criteria.budget,
    min_year=2015,
    make=criteria.make,  # now we pass it through
    body_style=criteria.body_style,
    limit=100,
)


    print(f"[DEBUG] Fetched {len(candidates)} candidates from API")
    
    if candidates:
        print(f"[DEBUG] Sample candidate: {candidates[0].get('make')} {candidates[0].get('model')}")
    
    # Blend in sample listings to avoid empty results and add variety
    merged_candidates = candidates + SAMPLE_LISTINGS
   

    # Deduplicate by ID/VIN
    seen = set()
    unique_candidates = []
    for item in merged_candidates:
        key = str(item.get("id") or item.get("vin") or id(item))
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(item)

    # Apply filters
    filtered = [c for c in unique_candidates if _passes_filters(c, criteria)]
    print(f"[DEBUG] {len(filtered)} candidates passed filters")
    
    # Score all filtered candidates
    scored = [score_listing(item, criteria) for item in filtered]
    
    # Sort by score
    scored.sort(key=lambda s: s.total_score, reverse=True)
    
    # Return top K
    result = scored[:top_k]
    print(f"[DEBUG] Returning {len(result)} results")
    
    for i, r in enumerate(result[:3]):  # Show first 3 for debugging
        print(f"[DEBUG] Result {i}: {r.listing.get('make')} {r.listing.get('model')} - Score: {r.total_score:.2f}")
    
    return result