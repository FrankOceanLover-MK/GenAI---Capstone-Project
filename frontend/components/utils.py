import os
import requests
from typing import Optional, Dict, Any, Tuple

DEFAULT_BASE = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))

class ApiError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"{status}: {message}")

def _handle_response(resp: requests.Response) -> Any:
    if 200 <= resp.status_code < 300:
        try:
            return resp.json()
        except Exception:
            return resp.text
    if resp.status_code == 401:
        raise ApiError(401, "Unauthorized. Check API key on backend (.env).")
    if resp.status_code == 429:
        raise ApiError(429, "Rate limit exceeded. Please wait and try again.")
    if resp.status_code == 404:
        raise ApiError(404, "Not found.")
    raise ApiError(resp.status_code, f"Server error ({resp.status_code}).")

def health(base: str = DEFAULT_BASE) -> Dict[str,Any]:
    r = requests.get(f"{base}/health", timeout=TIMEOUT)
    return _handle_response(r)

def get_car(vin: str, base: str = DEFAULT_BASE) -> Dict[str,Any]:
    r = requests.get(f"{base}/cars/{vin}", timeout=TIMEOUT)
    return _handle_response(r)

def get_summary(vin: str, base: str = DEFAULT_BASE) -> str:
    r = requests.get(f"{base}/cars/{vin}/summary", timeout=TIMEOUT)
    data = _handle_response(r)
    return data if isinstance(data, str) else (data.get("summary") if isinstance(data, dict) else str(data))

def try_recommendations(params: Dict[str,Any], base: str = DEFAULT_BASE) -> Tuple[Optional[str], Optional[Any]]:
    paths = ["/recommendations", "/cars/recommendations"]
    last_err = None
    for p in paths:
        try:
            r = requests.get(f"{base}{p}", params=params, timeout=TIMEOUT)
            data = _handle_response(r)
            return p, data
        except ApiError as e:
            last_err = e
            if e.status == 404:
                continue
            raise
        except requests.exceptions.Timeout:
            raise ApiError(408, "Request timed out.")
    if last_err:
        raise last_err
    return None, None

def openapi_has_recommendations(base: str = DEFAULT_BASE) -> bool:
    try:
        r = requests.get(f"{base}/openapi.json", timeout=TIMEOUT)
        spec = r.json()
        paths = spec.get("paths", {})
        return "/recommendations" in paths or "/cars/recommendations" in paths
    except Exception:
        return False
