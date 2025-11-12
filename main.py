from typing import Dict, Any

from fastapi import FastAPI, HTTPException

from external_apis import get_car_profile_from_vin
from schemas import CarProfile

app = FastAPI(title="GenAI Car Assistant Backend")


@app.get("/health")
def health():
    return {"status": "ok"}


def summarize_profile_for_llm(profile: Dict[str, Any]) -> str:
    """
    Turn the structured car profile into a short text summary that can be
    dropped straight into an LLM prompt.
    """
    econ = profile.get("economy", {}) or {}
    engine = profile.get("engine", {}) or {}

    return (
        f"{profile.get('year')} {profile.get('make')} {profile.get('model')} "
        f"{profile.get('trim') or ''} ({profile.get('type')}, built in {profile.get('origin')}). "
        f"Engine: {engine.get('displacement_l')}L, {engine.get('cylinders')} cylinders, "
        f"{engine.get('hp')} hp, fuel: {engine.get('fuel_type')}. "
        f"Approx. fuel economy: city {econ.get('city_mpg')} mpg, "
        f"highway {econ.get('highway_mpg')} mpg, mixed {econ.get('mixed_mpg')} mpg."
    )


@app.get("/cars/{vin}", response_model=CarProfile)
def get_car_by_vin(vin: str):
    """
    Main API endpoint: given a VIN, return a normalized CarProfile.
    """
    try:
        profile = get_car_profile_from_vin(vin)
        if not profile.get("year") or not profile.get("make") or not profile.get("model"):
            raise HTTPException(status_code=404, detail="Could not decode VIN")
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cars/{vin}/summary")
def get_car_summary(vin: str):
    """
    Convenience endpoint for the LLM / UI: return a short text summary
    of the car, ready for use inside prompts or explanations.
    """
    try:
        profile = get_car_profile_from_vin(vin)
        if not profile.get("year"):
            raise HTTPException(status_code=404, detail="Could not decode VIN")
        summary = summarize_profile_for_llm(profile)
        return {"vin": vin, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# To run the app, use the command:
# uvicorn main:app --reload
#
# To end the app/server, use Ctrl+C in the terminal.
