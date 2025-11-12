# schemas.py
from typing import Optional

from pydantic import BaseModel


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
