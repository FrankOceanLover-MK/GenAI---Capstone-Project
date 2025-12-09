from typing import List, Dict, Any
import os
import requests
import sys


# Ollama configuration - Note: No /v1 suffix for Ollama!
LLM_API_BASE = "http://127.0.0.1:11434"  # Use Ollama
LLM_MODEL_NAME = "llama3.2"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

print(f"[DEBUG] Loaded LLM_API_BASE: {LLM_API_BASE}", file=sys.stderr)
print(f"[DEBUG] Loaded LLM_MODEL_NAME: {LLM_MODEL_NAME}", file=sys.stderr)

class LLMError(RuntimeError):
    pass


def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 256,
    temperature: float = 0.3,
) -> str:
    """
    Call Ollama's /api/chat endpoint (OpenAI-compatible format).
    
    Ollama uses /api/chat, not /v1/chat/completions
    """

    # Remove any trailing slashes and /v1 suffix
    base = LLM_API_BASE.rstrip('/').replace('/v1', '')
    
    # Ollama uses /api/chat endpoint
    url = f"{base}/api/chat"
    
    print(f"[DEBUG] Calling LLM at {url}", file=sys.stderr)
    print(f"[DEBUG] Model: {LLM_MODEL_NAME}", file=sys.stderr)
    print(f"[DEBUG] Messages count: {len(messages)}", file=sys.stderr)
    
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    
    # Ollama doesn't need API key for local use
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    # Ollama's chat API format
    payload: Dict[str, Any] = {
        "model": LLM_MODEL_NAME,
        "messages": messages,
        "stream": False,  # Get complete response
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,  # Ollama uses num_predict instead of max_tokens
        }
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=LLM_TIMEOUT_SECONDS,
        )
        print(f"[DEBUG] Response status: {resp.status_code}", file=sys.stderr)
    except requests.exceptions.Timeout as e:
        print(f"[ERROR] Timeout: {e}", file=sys.stderr)
        raise LLMError(
            f"LLM request timed out after {LLM_TIMEOUT_SECONDS} seconds."
        ) from e
    except requests.RequestException as e:
        print(f"[ERROR] Request exception: {e}", file=sys.stderr)
        raise LLMError(
            f"Error contacting LLM server at {url}: {e}"
        ) from e

    if not (200 <= resp.status_code < 300):
        try:
            err = resp.json()
        except ValueError:
            err = resp.text
        print(f"[ERROR] LLM returned {resp.status_code}: {err}", file=sys.stderr)
        raise LLMError(f"LLM server returned {resp.status_code}: {err}")

    try:
        data = resp.json()
        print(f"[DEBUG] Response keys: {list(data.keys())}", file=sys.stderr)
    except ValueError as e:
        print(f"[ERROR] JSON parse failed: {resp.text[:200]}", file=sys.stderr)
        raise LLMError(
            f"Could not parse LLM response as JSON: {resp.text[:200]}"
        ) from e

    # Ollama response format: {"message": {"role": "assistant", "content": "..."}}
    message = data.get("message")
    if not message:
        print(f"[ERROR] Missing 'message' in response: {data}", file=sys.stderr)
        raise LLMError(f"LLM response missing 'message': {data}")
    
    content = message.get("content")
    if not isinstance(content, str):
        print(f"[ERROR] Invalid content type: {type(content)}, value: {content}", file=sys.stderr)
        raise LLMError(f"LLM response missing 'message.content': {data}")

    print(f"[DEBUG] Successfully got response with {len(content)} chars", file=sys.stderr)
    return content.strip()