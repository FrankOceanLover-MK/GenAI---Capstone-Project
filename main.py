from typing import Dict, Any, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from external_apis import get_car_profile_from_vin, ApiError as ExternalApiError  # type: ignore
from schemas import CarProfile
from llm_client import chat_completion, LLMError
from llm_prompts import build_car_advice_messages

app = FastAPI(title="GenAI Car Assistant Backend")


@app.get("/health")
def health() -> Dict[str, str]:
    """
    Simple health check used by the Streamlit frontend.
    """
    return {"status": "ok"}


def summarize_profile_for_llm(profile: Dict[str, Any]) -> str:
    """
    Turn a normalized CarProfile-like dict into a compact textual summary.

    This is meant to be fed into the LLM so it never has to guess specs itself.
    """
    year = profile.get("year")
    make = profile.get("make")
    model = profile.get("model")
    trim = profile.get("trim") or ""
    body_type = profile.get("type") or ""
    origin = profile.get("origin") or ""

    engine = profile.get("engine") or {}
    displacement = engine.get("displacement_l")
    cylinders = engine.get("cylinders")
    hp = engine.get("hp")
    fuel_type = engine.get("fuel_type") or "unknown fuel"

    econ = profile.get("economy") or {}
    city_mpg = econ.get("city_mpg")
    hwy_mpg = econ.get("highway_mpg")
    mixed_mpg = econ.get("mixed_mpg")

    parts: List[str] = []

    # Basic identity
    if year and make and model:
        name = f"{year} {make} {model}"
    else:
        name = f"{make or ''} {model or ''}".strip() or "This vehicle"
    if trim:
        name += f" {trim}"
    if body_type:
        name += f" ({body_type})"
    if origin:
        parts.append(f"{name}, built in {origin}.")
    else:
        parts.append(f"{name}.")

    # Engine
    engine_bits: List[str] = []
    if displacement:
        engine_bits.append(f"{displacement:.1f}L")
    if cylinders:
        engine_bits.append(f"{cylinders}-cylinder")
    if hp:
        engine_bits.append(f"{hp} hp")
    engine_desc = ", ".join(engine_bits) if engine_bits else "engine specs are partially unknown"
    parts.append(f"Engine: {engine_desc}, fuel: {fuel_type}.")

    # Economy
    if any(v is not None for v in (city_mpg, hwy_mpg, mixed_mpg)):
        eco_bits: List[str] = []
        if city_mpg:
            eco_bits.append(f"city {city_mpg:.0f} mpg")
        if hwy_mpg:
            eco_bits.append(f"highway {hwy_mpg:.0f} mpg")
        if mixed_mpg:
            eco_bits.append(f"mixed {mixed_mpg:.0f} mpg")
        eco_txt = ", ".join(eco_bits)
        parts.append(f"Approximate fuel economy: {eco_txt}.")
    else:
        parts.append("Fuel economy data is not available.")

    return " ".join(parts)


@app.get("/cars/{vin}", response_model=CarProfile)
def get_car(vin: str) -> CarProfile:
    """
    Return a normalized car profile for the given VIN.
    """
    try:
        profile_dict = get_car_profile_from_vin(vin)
    except ExternalApiError as e:  # type: ignore[misc]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not profile_dict or not profile_dict.get("year"):
        raise HTTPException(status_code=404, detail="Could not decode VIN")

    # Pydantic will validate / coerce for us
    return CarProfile(**profile_dict)


class CarSummaryResponse(BaseModel):
    vin: str
    summary: str


@app.get("/cars/{vin}/summary", response_model=CarSummaryResponse)
def get_car_summary(vin: str) -> CarSummaryResponse:
    """
    Get a short natural-language summary of the car for use in UIs or LLM prompts.
    """
    try:
        profile_dict = get_car_profile_from_vin(vin)
    except ExternalApiError as e:  # type: ignore[misc]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not profile_dict or not profile_dict.get("year"):
        raise HTTPException(status_code=404, detail="Could not decode VIN")

    summary = summarize_profile_for_llm(profile_dict)
    return CarSummaryResponse(vin=vin, summary=summary)


class ChatRequest(BaseModel):
    """
    Request body for the /chat endpoint.

    For now we require a VIN so we can ground the LLM in the decoded car profile.
    """
    question: str
    vin: str


class ChatResponse(BaseModel):
    vin: str
    summary: str
    answer: str


@app.post("/chat", response_model=ChatResponse)
def chat_with_llm(payload: ChatRequest) -> ChatResponse:
    """
    LLM-powered explanation endpoint.

    1. Decode the VIN into a structured car profile.
    2. Summarize that profile into text.
    3. Send the summary + user's question to the local Llama 3 server.
    4. Return the grounded natural-language answer.
    """
    vin = payload.vin.strip()
    if not vin:
        raise HTTPException(status_code=400, detail="vin must not be empty")

    try:
        profile_dict = get_car_profile_from_vin(vin)
    except ExternalApiError as e:  # type: ignore[misc]
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not profile_dict or not profile_dict.get("year"):
        raise HTTPException(status_code=404, detail="Could not decode VIN")

    summary = summarize_profile_for_llm(profile_dict)

    messages = build_car_advice_messages(
        user_question=payload.question,
        car_summary=summary,
    )

    try:
        answer = chat_completion(messages)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(vin=vin, summary=summary, answer=answer)
