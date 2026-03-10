from __future__ import annotations

import os
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, List, Literal

from pydantic import BaseModel
from google import genai
from google.genai import types


class LLMClient(Protocol):
    async def generate_json(self, *, system: str, user: str, timeout_s: int = 10) -> Dict[str, Any]:
        ...


@dataclass
class LLMConfig:
    provider: str = "disabled"  # "disabled" | "gemini"
    gemini_model: str = "gemini-2.5-flash"
    default_timeout_s: int = 10


class ExplanationJSON(BaseModel):
    mode: Literal["llm"]
    disclaimer: str
    bullets: List[str]
    narrative: str


def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Extract the first top-level JSON object from model text.

    Handles cases like:
      Here is the JSON requested:
      ```json
      {...}
      ```
    """
    if not text:
        raise ValueError("Empty text")

    cleaned = text.strip()

    # Remove fenced code blocks if present.
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Fast path: full text is already JSON.
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Extract first {...} block.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in text: {cleaned[:300]}")

    candidate = cleaned[start : end + 1]
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except Exception as e:
        raise ValueError(f"Failed to parse extracted JSON: {e} :: {candidate[:500]}")

    raise ValueError(f"Extracted JSON is not an object: {candidate[:300]}")


class GeminiVertexClient:
    def __init__(self, *, model: str = "gemini-2.5-flash"):
        self.model = model

        self.project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "").strip()

        if not self.project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is not set")
        if not self.location:
            raise ValueError("GOOGLE_CLOUD_LOCATION is not set")

        self.client = genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
        )

    def _call_once(self, *, system: str, user: str, max_output_tokens: int) -> Dict[str, Any]:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=0.0,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
                response_schema=ExplanationJSON,
                # Keep thought-token usage minimal to avoid truncating short JSON replies.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        parsed = getattr(response, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, BaseModel):
                return parsed.model_dump()
            if isinstance(parsed, dict):
                return parsed

        text = getattr(response, "text", None)
        if not text:
            raise ValueError(f"Gemini returned empty text: {response}")

        return _extract_json_object(text)

    async def generate_json(self, *, system: str, user: str, timeout_s: int = 10) -> Dict[str, Any]:
        try:
            return self._call_once(system=system, user=user, max_output_tokens=300)
        except Exception as e1:
            print(f"[llm_client] first attempt failed: {type(e1).__name__}: {e1}")
            return self._call_once(system=system, user=user, max_output_tokens=220)


def build_llm_client(cfg: LLMConfig) -> Optional[LLMClient]:
    provider = (cfg.provider or "disabled").lower().strip()

    if provider == "disabled":
        return None

    if provider == "gemini":
        model = os.getenv("GEMINI_MODEL", cfg.gemini_model).strip() or cfg.gemini_model
        try:
            return GeminiVertexClient(model=model)
        except Exception as e:
            print(f"[llm_client] client init failed: {type(e).__name__}: {e}")
            return None

    return None