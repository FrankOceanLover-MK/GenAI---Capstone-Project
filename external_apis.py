import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()  # loads .env from project root

AUTO_DEV_API_KEY = os.getenv("AUTO_DEV_API_KEY")


class ApiError(RuntimeError):
    pass


# -------------------------------------------------------------------
# Simple in-memory TTL cache (24 hours)
# -------------------------------------------------------------------

_CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL = 60 * 60 * 24  # 24 hours


def cache_get(key: str):
    now = time.time()
    item = _CACHE.get(key)
    if not item:
        return None
    ts, value = item
    if now - ts > CACHE_TTL:
        # expired
        _CACHE.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any):
    _CACHE[key] = (time.time(), value)


# -------------------------------------------------------------------
# 1) AUTO.DEV – VIN decode
# -------------------------------------------------------------------

def auto_dev_vin_decode(vin: str) -> Dict[str, Any]:
    """
    Call Auto.dev VIN Decode API and return JSON.
    Docs: GET https://api.auto.dev/vin/{vin}
    Authorization: Bearer <API_KEY>
    """
    if not AUTO_DEV_API_KEY:
        raise ApiError("AUTO_DEV_API_KEY is not set")

    cache_key = f"auto_dev_vin:{vin}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"https://api.auto.dev/vin/{vin}"
    headers = {
        "Authorization": f"Bearer {AUTO_DEV_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    cache_set(cache_key, data)
    return data


# (Unused, but kept here if you ever upgrade plans)
def auto_dev_specs(vin: str) -> Dict[str, Any]:
    if not AUTO_DEV_API_KEY:
        raise ApiError("AUTO_DEV_API_KEY is not set")

    url = f"https://api.auto.dev/specs/{vin}"
    headers = {
        "Authorization": f"Bearer {AUTO_DEV_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code == 402:
        # specs endpoint not available on this plan
        print("Auto.dev specs endpoint not available on this plan (402 Payment Required)")
        return {}

    resp.raise_for_status()
    return resp.json()


# -------------------------------------------------------------------
# 2) NHTSA vPIC – decode VIN (free, no key)
# -------------------------------------------------------------------

def nhtsa_decode_vin(vin: str, model_year: int | None = None) -> Dict[str, Any]:
    """
    Use NHTSA vPIC DecodeVinValues endpoint (returns a flat JSON object).
    Docs: /api/vehicles/DecodeVinValues/{vin}?format=json&modelyear=YYYY
    """
    cache_key = f"nhtsa_vin:{vin}:{model_year or ''}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    base = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues"
    params: Dict[str, Any] = {"format": "json"}
    if model_year:
        params["modelyear"] = model_year

    url = f"{base}/{vin}"
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("Results") or []
    flat = results[0] if results else {}

    cache_set(cache_key, flat)
    return flat


# -------------------------------------------------------------------
# 3) CarQuery – basic make/model/year trims
# -------------------------------------------------------------------

def carquery_get_trims(make: str, model: str, year: int) -> List[Dict[str, Any]]:
    """
    Call CarQuery getTrims to get trims/specs by year/make/model.
    If CarQuery blocks us (403), just return [] so the rest of the
    pipeline can still work.
    """
    cache_key = f"carquery_trims:{year}:{make}:{model}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = "https://www.carqueryapi.com/api/0.3/"
    params = {
        "cmd": "getTrims",
        "make": make,
        "model": model,
        "year": year,
    }
    # some services block requests without a browser-like User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CarWiseBackend/0.1; +https://example.com)"
    }

    resp = requests.get(url, params=params, headers=headers, timeout=10)

    if resp.status_code == 403:
        print("CarQuery returned 403 Forbidden; skipping trims and returning [].")
        cache_set(cache_key, [])
        return []

    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        print(f"CarQuery error: {e}")
        cache_set(cache_key, [])
        return []

    data = resp.json()
    trims = data.get("Trims", []) or []
    cache_set(cache_key, trims)
    return trims


# -------------------------------------------------------------------
# 4) helpers for fuel economy conversions
# -------------------------------------------------------------------

def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def l_per_100km_to_mpg(l_per_100km: Optional[float]) -> Optional[float]:
    """
    Convert liters/100km to miles per gallon.
    If input is None or 0, return None.
    """
    if not l_per_100km:
        return None
    # standard conversion factor
    return round(235.214 / l_per_100km, 1)


def get_economy_from_carquery(year: int, make: str, model: str) -> Dict[str, Any]:
    """
    Use CarQuery trims as the source of fuel economy data.
    """
    trims = carquery_get_trims(make=make, model=model, year=year)
    if not trims:
        return {}

    # simplest choice: just take the first trim
    t = trims[0]

    city_l = _parse_float(t.get("model_lkm_city"))
    hwy_l = _parse_float(t.get("model_lkm_hwy"))
    mixed_l = _parse_float(t.get("model_lkm_mixed"))

    economy: Dict[str, Any] = {
        "fuel_type": t.get("model_engine_fuel"),
        "city_l_per_100km": city_l,
        "highway_l_per_100km": hwy_l,
        "mixed_l_per_100km": mixed_l,
        "city_mpg": l_per_100km_to_mpg(city_l),
        "highway_mpg": l_per_100km_to_mpg(hwy_l),
        "mixed_mpg": l_per_100km_to_mpg(mixed_l),
        "source": "carquery",
        "trim_used": t.get("model_trim"),
    }

    return economy


# -------------------------------------------------------------------
# 5) Helper for Integer Parsing (Fixes EV Crash)
# -------------------------------------------------------------------

def _parse_int(value: Any) -> Optional[int]:
    if not value:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


# -------------------------------------------------------------------
# 6) NHTSA 5-Star Safety Ratings (The Enrichment)
# -------------------------------------------------------------------

def get_safety_rating(year: int, make: str, model: str) -> Optional[int]:
    """
    Query NHTSA 5-Star Safety Ratings.
    """
    cache_key = f"nhtsa_safety:{year}:{make}:{model}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    if not year or not make or not model:
        return None

    try:
        base_url = "https://api.nhtsa.gov/SafetyRatings"
        query_url = f"{base_url}/modelyear/{year}/make/{make}/model/{model}"
        
        resp = requests.get(query_url, timeout=5)
        if resp.status_code != 200:
            cache_set(cache_key, None)
            return None
            
        data = resp.json()
        results = data.get("Results", [])
        if not results:
            cache_set(cache_key, None)
            return None
            
        vehicle_id = results[0].get("VehicleId")
        
        rating_url = f"{base_url}/VehicleId/{vehicle_id}"
        resp_rating = requests.get(rating_url, timeout=5)
        rating_data = resp_rating.json()
        rating_results = rating_data.get("Results", [])
        
        if not rating_results:
            cache_set(cache_key, None)
            return None
            
        overall_str = rating_results[0].get("OverallRating", "")
        try:
            rating = int(overall_str)
        except ValueError:
            rating = None
            
        cache_set(cache_key, rating)
        return rating

    except Exception as e:
        print(f"NHTSA Safety API Error: {e}")
        return None


# -------------------------------------------------------------------
# 7) High-level profile helper
# -------------------------------------------------------------------

def get_car_profile_from_vin(vin: str) -> Dict[str, Any]:
    """
    High-level helper: given a VIN, combine Auto.dev (VIN decode),
    NHTSA (extra specs), and CarQuery (fuel economy).
    """

    # 1) Decode VIN with Auto.dev – this is our primary source for year/make/model.
    auto_data = auto_dev_vin_decode(vin)

    # 2) Decode VIN with NHTSA – secondary source and extra technical details.
    nhtsa_data = nhtsa_decode_vin(vin)

    # 3) Pull core identity (year / make / model).
    #    Prefer Auto.dev's nested "vehicle" object, but fall back to NHTSA / top-level.
    vehicle = auto_data.get("vehicle", {}) or {}

    # Year may be int (Auto.dev) or string (NHTSA), so be a bit defensive.
    year = vehicle.get("year")
    if year is None:
        model_year_str = nhtsa_data.get("ModelYear")
        year = int(model_year_str) if model_year_str else None

    make = vehicle.get("make") or auto_data.get("make") or nhtsa_data.get("Make")
    model = vehicle.get("model") or auto_data.get("model") or nhtsa_data.get("Model")

    # Trim: Auto.dev has a nice top-level "trim"; fall back to NHTSA's "Trim".
    trim = auto_data.get("trim") or nhtsa_data.get("Trim")

    # 4) Ask CarQuery for fuel economy data (city/highway/mixed MPG + fuel type).
    economy = get_economy_from_carquery(year=year, make=make, model=model)
    
    # 5) Safety
    safety_stars = get_safety_rating(year, make, model)

    # 6) Build a clean, compact profile that your app / LLM can rely on.
    profile: Dict[str, Any] = {
        "vin": vin,
        "year": year,
        "make": make,
        "model": model,
        "trim": trim,
        "type": auto_data.get("type"),      # e.g. "Passenger Car"
        "origin": auto_data.get("origin"),  # e.g. "Germany"

        # Engine summary from NHTSA + fuel type from CarQuery when available.
        "engine": {
            "displacement_l": _parse_float(nhtsa_data.get("DisplacementL")),
            "cylinders": _parse_int(nhtsa_data.get("EngineCylinders")),
            "hp": _parse_int(nhtsa_data.get("EngineHP")),
            "fuel_type": economy.get("fuel_type") or nhtsa_data.get("FuelTypePrimary"),
        },

        # Fuel economy in MPG from CarQuery helper.
        "economy": {
            "city_mpg": economy.get("city_mpg"),
            "highway_mpg": economy.get("highway_mpg"),
            "mixed_mpg": economy.get("mixed_mpg"),
            "source": economy.get("source"),
        },
        
        "safety": {
            "nhtsa_stars": safety_stars,
            "source": "nhtsa"
        }
    }

    return profile


# -------------------------------------------------------------------
# 8) Auto.dev Listings Search (The New Fetcher)
# -------------------------------------------------------------------

def _map_auto_dev_listing_to_schema(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter: Maps raw Auto.dev listing JSON to our SearchListing schema.
    """
    vehicle = item.get("vehicle", {}) or {}
    retail = item.get("retailListing", {}) or {}

    price = retail.get("price")
    mileage = retail.get("miles")
    distance = item.get("distance")
    vin = vehicle.get("vin") or item.get("vin")

    # Get URL
    listing_url = (
        item.get("vdp_url") or item.get("vdpUrl") or retail.get("url") or item.get("url")
    )

    return {
        "id": item.get("id") or str(vin),
        "year": vehicle.get("year"),
        "make": vehicle.get("make"),
        "model": vehicle.get("model"),
        "trim": item.get("trim") or vehicle.get("trim"),
        "price": price,
        "mileage": mileage,
        "distance_miles": distance,
        "fuel_type": vehicle.get("fuel"),
        "body_style": vehicle.get("bodyStyle"),
        "city_mpg": vehicle.get("cityMpg"),
        "highway_mpg": vehicle.get("highwayMpg"),
        # Optimization: Skip safety rating for search results to be fast
        "safety_rating": None, 
        "source": "auto.dev",
        "vin": vin,
        "listing_url": listing_url,
    }


def fetch_active_listings(
    budget: Optional[float] = None,
    min_year: Optional[int] = None,
    make: Optional[str] = None,
    body_style: Optional[str] = None,
    # NEW: Added Model filtering
    model: Optional[str] = None,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Call Auto.dev GET /listings to find real cars.
    """
    if not AUTO_DEV_API_KEY:
        print("Warning: AUTO_DEV_API_KEY not set. Returning empty results.")
        return []

    url = "https://api.auto.dev/listings"
    
    # Updated Params based on Auto.dev Docs
    params = {
        "apikey": AUTO_DEV_API_KEY, 
        "limit": limit,
    }
    
    # Use dot-notation keys as per Auto.dev documentation
    if budget:
        # Auto.dev often uses ranges for price, e.g., "1-30000"
        params["retailListing.price"] = f"1-{int(budget)}"
    if min_year:
        params["vehicle.year"] = f"{min_year}-2025"
    if make:
        params["vehicle.make"] = make
    if body_style:
        params["vehicle.bodyStyle"] = body_style
    # NEW: Pass model to API
    if model:
        params["vehicle.model"] = model

    headers = {
        "Authorization": f"Bearer {AUTO_DEV_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        
        if resp.status_code != 200:
            print(f"Auto.dev listings error: {resp.status_code} - {resp.text}")
            return []
            
        data = resp.json()
        
        # FIX: The key is 'data', not 'records'
        raw_listings = data.get("data", [])
        
        clean_listings = []
        for raw in raw_listings:
            try:
                clean = _map_auto_dev_listing_to_schema(raw)
                # Ensure we have the basics
                if clean["year"] and clean["make"] and clean["model"]:
                    clean_listings.append(clean)
            except Exception as e:
                # print(f"Skipping malformed listing: {e}")
                continue
                
        return clean_listings

    except Exception as e:
        print(f"Failed to fetch listings: {e}")
        return []