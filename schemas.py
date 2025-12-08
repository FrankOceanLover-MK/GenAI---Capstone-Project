# schemas.py
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class EngineSummary(BaseModel):
    displacement_l: Optional[float] = None
    cylinders: Optional[int] = None
    hp: Optional[int] = None
    fuel_type: Optional[str] = None


class EconomySummary(BaseModel):
    city_mpg: Optional[float] = None
    highway_mpg: Optional[float] = None
    mixed_mpg: Optional[float] = None
    source: Optional[str] = None


class CarProfile(BaseModel):
    vin: str
    year: Optional[int]
    make: Optional[str]
    model: Optional[str]
    trim: Optional[str]
    type: Optional[str]
    origin: Optional[str]
    engine: EngineSummary
    economy: EconomySummary

class ScoreBreakdownModel(BaseModel):
    price: float
    mileage: float
    distance: float
    economy: float
    safety: float
    total: float


class SearchCriteriaModel(BaseModel):
    budget: Optional[float] = Field(None, description="Maximum budget in USD")
    max_distance: Optional[float] = Field(None, description="Max delivery distance in miles")
    body_style: Optional[str] = Field(None, description="Desired body style (SUV, Sedan, etc.)")
    fuel_type: Optional[str] = Field(None, description="Fuel type preference (Gasoline, Hybrid, Electric)")


class SearchListing(BaseModel):
    id: str
    year: int
    make: str
    model: str
    trim: Optional[str] = None
    price: Optional[float] = None
    mileage: Optional[float] = None
    distance_miles: Optional[float] = None
    fuel_type: Optional[str] = None
    body_style: Optional[str] = None
    city_mpg: Optional[float] = None
    highway_mpg: Optional[float] = None
    safety_rating: Optional[float] = None
    source: Optional[str] = None


class SearchResult(BaseModel):
    listing: SearchListing
    score: ScoreBreakdownModel


class SearchResponse(BaseModel):
    results: List[SearchResult]
    criteria_applied: Dict[str, Any]