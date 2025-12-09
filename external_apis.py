import os
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse

import requests
from dotenv import load_dotenv

load_dotenv()

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
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Validate response has required fields
        if not data or not isinstance(data, dict):
            raise ApiError(f"Invalid response from Auto.dev for VIN {vin}")
        
        cache_set(cache_key, data)
        return data
    except requests.exceptions.RequestException as e:
        raise ApiError(f"Auto.dev API error: {str(e)}")


# -------------------------------------------------------------------
# 2) NHTSA vPIC – decode VIN
# -------------------------------------------------------------------

def nhtsa_decode_vin(vin: str, model_year: int | None = None) -> Dict[str, Any]:
    """
    Use NHTSA vPIC DecodeVinValues endpoint.
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
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("Results") or []
        flat = results[0] if results else {}

        cache_set(cache_key, flat)
        return flat
    except requests.exceptions.RequestException as e:
        print(f"NHTSA API warning: {e}")
        return {}


# -------------------------------------------------------------------
# 3) CarQuery – basic make/model/year trims
# -------------------------------------------------------------------

def carquery_get_trims(make: str, model: str, year: int) -> List[Dict[str, Any]]:
    """
    Call CarQuery getTrims to get trims/specs by year/make/model.
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
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CarWiseBackend/0.1; +https://example.com)"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)

        if resp.status_code == 403:
            print("CarQuery returned 403 Forbidden; skipping trims.")
            cache_set(cache_key, [])
            return []

        resp.raise_for_status()
        data = resp.json()
        trims = data.get("Trims", []) or []
        cache_set(cache_key, trims)
        return trims
    except requests.exceptions.RequestException as e:
        print(f"CarQuery error: {e}")
        cache_set(cache_key, [])
        return []


# -------------------------------------------------------------------
# 4) Fuel economy helpers
# -------------------------------------------------------------------

def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> Optional[int]:
    if not value:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def l_per_100km_to_mpg(l_per_100km: Optional[float]) -> Optional[float]:
    """Convert liters/100km to miles per gallon."""
    if not l_per_100km or l_per_100km <= 0:
        return None
    return round(235.214 / l_per_100km, 1)


def get_economy_from_carquery(year: int, make: str, model: str) -> Dict[str, Any]:
    """
    Use CarQuery trims as the source of fuel economy data.
    """
    trims = carquery_get_trims(make=make, model=model, year=year)
    if not trims:
        return {}

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
# 5) NHTSA 5-Star Safety Ratings (FIXED)
# -------------------------------------------------------------------

def get_safety_rating(year: int, make: str, model: str) -> Optional[int]:
    """
    Query NHTSA 5-Star Safety Ratings with proper URL encoding.
    """
    cache_key = f"nhtsa_safety:{year}:{make}:{model}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    if not year or not make or not model:
        return None

    try:
        # FIXED: Properly encode make and model for URLs
        # This handles spaces and special characters correctly
        make_encoded = urllib.parse.quote(str(make).strip())
        model_encoded = urllib.parse.quote(str(model).strip())
        
        base_url = "https://api.nhtsa.gov/SafetyRatings"
        query_url = f"{base_url}/modelyear/{year}/make/{make_encoded}/model/{model_encoded}"
        
        resp = requests.get(query_url, timeout=10)
        
        if resp.status_code != 200:
            cache_set(cache_key, None)
            return None
            
        data = resp.json()
        results = data.get("Results", [])
        
        if not results:
            cache_set(cache_key, None)
            return None
            
        vehicle_id = results[0].get("VehicleId")
        if not vehicle_id:
            cache_set(cache_key, None)
            return None

        # Get rating for that vehicle
        rating_url = f"{base_url}/VehicleId/{vehicle_id}"
        resp_rating = requests.get(rating_url, timeout=10)
        
        if resp_rating.status_code != 200:
            cache_set(cache_key, None)
            return None
            
        rating_data = resp_rating.json()
        rating_results = rating_data.get("Results", [])
        
        if not rating_results:
            cache_set(cache_key, None)
            return None
            
        overall_str = rating_results[0].get("OverallRating", "")
        
        try:
            rating = int(overall_str) if overall_str else None
        except ValueError:
            rating = None
            
        cache_set(cache_key, rating)
        return rating

    except Exception as e:
        print(f"NHTSA Safety API Error for {year} {make} {model}: {e}")
        cache_set(cache_key, None)
        return None


# -------------------------------------------------------------------
# 6) High-level profile helper
# -------------------------------------------------------------------

def get_car_profile_from_vin(vin: str) -> Dict[str, Any]:
    """
    Combine Auto.dev, NHTSA, and CarQuery data into one normalized profile.
    """
    # Decode VIN with Auto.dev
    auto_data = auto_dev_vin_decode(vin)

    # Decode VIN with NHTSA
    nhtsa_data = nhtsa_decode_vin(vin)

    # Extract core identity
    vehicle = auto_data.get("vehicle", {}) or {}

    year = vehicle.get("year")
    if year is None:
        model_year_str = nhtsa_data.get("ModelYear")
        year = int(model_year_str) if model_year_str else None

    make = vehicle.get("make") or auto_data.get("make") or nhtsa_data.get("Make")
    model = vehicle.get("model") or auto_data.get("model") or nhtsa_data.get("Model")
    trim = auto_data.get("trim") or nhtsa_data.get("Trim")

    # Get fuel economy data
    economy = {}
    if year and make and model:
        try:
            economy = get_economy_from_carquery(year=year, make=make, model=model)
        except Exception as e:
            print(f"CarQuery economy lookup failed: {e}")

    # Get safety rating
    safety_stars = None
    if year and make and model:
        try:
            safety_stars = get_safety_rating(year, make, model)
        except Exception as e:
            print(f"Safety rating lookup failed: {e}")

    # Build profile
    profile: Dict[str, Any] = {
        "vin": vin,
        "year": year,
        "make": make,
        "model": model,
        "trim": trim,
        "type": auto_data.get("type"),
        "origin": auto_data.get("origin"),

        "engine": {
            "displacement_l": _parse_float(nhtsa_data.get("DisplacementL")),
            "cylinders": _parse_int(nhtsa_data.get("EngineCylinders")),
            "hp": _parse_int(nhtsa_data.get("EngineHP")),
            "fuel_type": economy.get("fuel_type") or nhtsa_data.get("FuelTypePrimary"),
        },

        "economy": {
            "city_mpg": economy.get("city_mpg"),
            "highway_mpg": economy.get("highway_mpg"),
            "mixed_mpg": economy.get("mixed_mpg"),
            "source": economy.get("source"),
        },

        "safety": {
            "nhtsa_stars": safety_stars,
            "source": "nhtsa" if safety_stars else None
        }
    }

    return profile


# -------------------------------------------------------------------
# 7) Auto.dev Listings Search (Enhanced with better error handling)
# -------------------------------------------------------------------

def _map_auto_dev_listing_to_schema(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map Auto.dev listing format to our internal schema."""
    vehicle = item.get("vehicle", {}) or {}
    retail = item.get("retailListing", {}) or {}

    price = retail.get("price")
    mileage = retail.get("miles")
    distance = item.get("distance")

    vin = vehicle.get("vin") or item.get("vin")
    
    # Get listing ID for constructing URL
    listing_id = item.get("id")
    
    # Try multiple URL sources
    listing_url = None
    url_sources = [
        retail.get("vdp"),        # Primary field
        item.get("vdp_url"),
        item.get("vdpUrl"),
        retail.get("url"),
        item.get("url"),
    ]
    
    for url in url_sources:
        if url and isinstance(url, str) and url.startswith(("http://", "https://")):
            listing_url = url
            break
    
    # If no URL found, construct one from listing ID
    if not listing_url and listing_id:
        listing_url = f"https://auto.dev/listings/{listing_id}"
    elif not listing_url and vin:
        listing_url = f"https://auto.dev/inventory/{vin}"

    return {
        "id": item.get("id") or str(vin) or f"listing_{id(item)}",
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
        "safety_rating": None,  # Can be enriched later
        "source": "auto.dev",
        "vin": vin,
        "listing_url": listing_url,
    }


def fetch_active_listings(
    budget: Optional[float] = None,
    min_year: Optional[int] = None,
    make: Optional[str] = None,
    body_style: Optional[str] = None,
    limit: int = 15
) -> List[Dict[str, Any]]:
    """
    Call Auto.dev GET /listings to find real cars with enhanced error handling.
    """
    if not AUTO_DEV_API_KEY:
        print("Warning: AUTO_DEV_API_KEY not set. Returning empty results.")
        return []

    url = "https://api.auto.dev/listings"
    
    params = {
        "apikey": AUTO_DEV_API_KEY,
        "limit": limit,
    }
    
    # Build filters based on Auto.dev API documentation
    if budget:
        params["retailListing.price"] = f"1-{int(budget)}"
    if min_year:
        params["vehicle.year"] = f"{min_year}-2025"
    if make:
        params["vehicle.make"] = make
    if body_style:
        params["vehicle.bodyStyle"] = body_style

    headers = {
        "Authorization": f"Bearer {AUTO_DEV_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        
        if resp.status_code != 200:
            print(f"Auto.dev listings error: {resp.status_code}")
            try:
                error_detail = resp.json()
                print(f"Error details: {error_detail}")
            except:
                print(f"Response text: {resp.text[:500]}")
            return []
            
        data = resp.json()
        raw_listings = data.get("data", [])
        
        if not raw_listings:
            print("No listings returned from Auto.dev")
            return []
        
        clean_listings = []
        for raw in raw_listings:
            try:
                clean = _map_auto_dev_listing_to_schema(raw)
                # Validate minimum required fields
                if clean.get("year") and clean.get("make") and clean.get("model"):
                    clean_listings.append(clean)
                else:
                    print(f"Skipping listing with missing core fields: {clean.get('id')}")
            except Exception as e:
                print(f"Error mapping listing: {e}")
                continue
                
        print(f"Successfully processed {len(clean_listings)} listings from Auto.dev")
        return clean_listings

    except requests.exceptions.Timeout:
        print("Auto.dev listings request timed out")
        return []
    except Exception as e:
        print(f"Failed to fetch listings: {e}")
        return []