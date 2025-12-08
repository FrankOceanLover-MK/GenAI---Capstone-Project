"""
Talking to a local Llama 3 (or other OpenAI-compatible) server.

By default this assumes an OpenAI-style /v1/chat/completions endpoint, which is what
many local deployments expose. You can adjust the environment variables below to 
match your setup.
"""

from typing import List, Dict, Any
import os
import requests


LLM_API_BASE = os.getenv("LLM_API_BASE", "http://127.0.0.1:11434/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama3")
LLM_API_KEY = os.getenv("LLM_API_KEY")  # optional, for hosted providers

LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))


class LLMError(RuntimeError):
    pass


def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 512,
    temperature: float = 0.2,
) -> str:
    """
    Call the LLM's chat completion endpoint with the provided messages.

    `messages` should be a list of {"role": "...", "content": "..."} dicts.

    Returns the assistant's message content as a string, or raises LLMError on failure.
    """
    if not messages:
        raise LLMError("messages must not be empty")

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
        resp = requests.post(url, json=payload, headers=headers, timeout=LLM_TIMEOUT_SECONDS)
    except requests.exceptions.Timeout as e:
        raise LLMError(f"LLM request timed out after {LLM_TIMEOUT_SECONDS}s") from e
    except requests.exceptions.RequestException as e:
        raise LLMError(f"Error contacting LLM server at {url}: {e}") from e

    if resp.status_code < 200 or resp.status_code >= 300:
        # Try to surface any error message the server returned
        try:
            data = resp.json()
            message = data.get("error", {}).get("message") or data
        except Exception:
            message = resp.text
        raise LLMError(f"LLM server returned {resp.status_code}: {message}")

    try:
        data = resp.json()
    except ValueError as e:
        raise LLMError(f"Could not parse LLM response as JSON: {resp.text[:200]}") from e

    # OpenAI-style response: choices[0].message.content
    choices = data.get("choices")
    if not choices:
        raise LLMError(f"LLM response missing 'choices': {data}")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise LLMError(f"LLM response missing 'message.content': {data}")

    return content.strip()
