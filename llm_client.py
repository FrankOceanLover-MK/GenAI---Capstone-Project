from typing import List, Dict, Any
import os
import requests

# Defaults are set up for Ollama running locally
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://127.0.0.1:11434/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama3.2")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")  # Ollama ignores this
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))


class LLMError(RuntimeError):
    pass


def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 256,
    temperature: float = 0.3,
) -> str:
    """
    Call an OpenAI-compatible /v1/chat/completions endpoint and return text.
    'messages' is the usual list of {role, content} dicts.
    """

    url = f"{LLM_API_BASE.rstrip('/')}/chat/completions"
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload: Dict[str, Any] = {
        "model": LLM_MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=LLM_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout as e:
        raise LLMError(
            f"LLM request timed out after {LLM_TIMEOUT_SECONDS} seconds."
        ) from e
    except requests.RequestException as e:
        raise LLMError(
            f"Error contacting LLM server at {LLM_API_BASE}: {e}"
        ) from e

    if not (200 <= resp.status_code < 300):
        try:
            err = resp.json()
        except ValueError:
            err = resp.text
        raise LLMError(f"LLM server returned {resp.status_code}: {err}")

    try:
        data = resp.json()
    except ValueError as e:
        raise LLMError(
            f"Could not parse LLM response as JSON: {resp.text[:200]}"
        ) from e

    # OpenAI-style: choices[0].message.content
    choices = data.get("choices")
    if not choices:
        raise LLMError(f"LLM response missing 'choices': {data}")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise LLMError(f"LLM response missing 'message.content': {data}")

    return content.strip()
