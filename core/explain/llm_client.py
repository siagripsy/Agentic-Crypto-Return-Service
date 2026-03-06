# core/explain/llm_client.py
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

import httpx


# -----------------------------
# Provider-agnostic interface
# -----------------------------
class LLMClient(Protocol):
    async def generate_json(self, *, system: str, user: str, timeout_s: int = 10) -> Dict[str, Any]:
        ...


@dataclass
class LLMConfig:
    provider: str = "disabled"  # "disabled" | "gemini"
    # If you deploy on GCP later, you can swap to Vertex auth (OIDC) and remove API keys.
    gemini_api_key_env: str = "GEMINI_API_KEY"
    gemini_model: str = "gemini-1.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    default_timeout_s: int = 10


# -----------------------------
# Gemini (API-key) client
# -----------------------------
class GeminiClient:
    """
    Minimal Gemini REST client that requests *JSON only*.

    Notes:
    - This uses API key auth (good for local testing).
    - For GCP deployment, you likely switch to Vertex AI (service account / workload identity),
      but you can keep this class and later add a VertexGeminiClient.
    """

    def __init__(self, *, api_key: str, model: str = "gemini-1.5-flash", base_url: str = "https://generativelanguage.googleapis.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate_json(self, *, system: str, user: str, timeout_s: int = 10) -> Dict[str, Any]:
        """
        Returns a dict. If Gemini doesn't return valid JSON, raises ValueError.
        """
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        params = {"key": self.api_key}

        # Gemini schema: contents -> parts
        # Force JSON by instruction + response MIME. Some accounts support responseMimeType.
        payload: Dict[str, Any] = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]},
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 512,
                # Best-effort: some versions accept this:
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.post(url, params=params, json=payload)
            r.raise_for_status()
            data = r.json()

        # Extract text
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise ValueError(f"Gemini response parse error: {e} :: {data}")

        # Parse JSON
        try:
            return json.loads(text)
        except Exception as e:
            raise ValueError(f"Gemini did not return valid JSON: {e} :: {text}")


def build_llm_client(cfg: LLMConfig) -> Optional[LLMClient]:
    """
    Factory: returns None when disabled or misconfigured (so engine can fall back).
    """
    provider = (cfg.provider or "disabled").lower().strip()
    if provider == "disabled":
        return None

    if provider == "gemini":
        api_key = os.getenv(cfg.gemini_api_key_env, "").strip()
        if not api_key:
            return None
        return GeminiClient(api_key=api_key, model=cfg.gemini_model, base_url=cfg.gemini_base_url)

    # Unknown provider
    return None