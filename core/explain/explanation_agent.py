# core/explain/explanation_agent.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal

from core.explain.fallback import explain_forecast_fallback, explain_portfolio_fallback
from core.explain.llm_client import LLMConfig, build_llm_client


ExplainTarget = Literal["forecast", "portfolio"]


SYSTEM_PROMPT = """You are an assistant embedded inside a crypto risk/portfolio API.
Your job is to explain the numeric output clearly, conservatively, and without hype.

Rules:
- Do NOT give financial advice. Do NOT predict certainty. Avoid promises.
- Keep it short: 5-8 bullets + 1 short paragraph.
- Use only the provided JSON payload; do not invent data.
- Explicitly mention uncertainty and simulation-based nature.
- Return STRICT JSON only, matching the schema below.

Schema:
{
  "mode": "llm",
  "disclaimer": "<string>",
  "bullets": ["<string>", ...],
  "narrative": "<string>"
}
"""


def _default_disclaimer() -> str:
    return (
        "Disclaimer: This explanation is informational only and not financial advice. "
        "Crypto returns are uncertain; outputs reflect model assumptions and simulated scenarios."
    )


@dataclass
class ExplainConfig:
    enabled: bool = True
    provider: str = "disabled"  # "disabled" | "gemini"
    timeout_s: int = 10


class ExplanationEngine:
    """
    LLM-first with fallback. Safe for deployment:
    - If LLM disabled, missing API key, network error, or invalid JSON -> fallback.
    - Always returns a dict with {mode, disclaimer, bullets, narrative}.
    """

    def __init__(self, cfg: ExplainConfig):
        self.cfg = cfg
        llm_cfg = LLMConfig(
            provider=cfg.provider,
            default_timeout_s=cfg.timeout_s,
        )
        self._client = build_llm_client(llm_cfg)

    async def explain(self, *, target: ExplainTarget, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.cfg.enabled:
            return self._fallback(target, payload)

        if self._client is None:
            return self._fallback(target, payload)

        user_prompt = (
            f"Target: {target}\n\n"
            "Here is the API response payload (JSON). Explain it.\n\n"
            f"{payload}"
        )

        try:
            out = await self._client.generate_json(system=SYSTEM_PROMPT, user=user_prompt, timeout_s=self.cfg.timeout_s)
            # minimal validation
            if not isinstance(out, dict):
                raise ValueError("LLM output not a dict")
            out.setdefault("mode", "llm")
            out.setdefault("disclaimer", _default_disclaimer())
            out.setdefault("bullets", [])
            out.setdefault("narrative", "")
            return out
        except Exception:
            return self._fallback(target, payload)

    def _fallback(self, target: ExplainTarget, payload: Dict[str, Any]) -> Dict[str, Any]:
        if target == "portfolio":
            return explain_portfolio_fallback(payload)
        return explain_forecast_fallback(payload)


def load_explanation_engine_from_env() -> ExplanationEngine:
    """
    Convenience loader for FastAPI:
    - EXPLAIN_ENABLED=1/0
    - EXPLAIN_PROVIDER=disabled|gemini
    - EXPLAIN_TIMEOUT_S=10
    - GEMINI_API_KEY=... (only if provider=gemini)
    """
    enabled = os.getenv("EXPLAIN_ENABLED", "1").strip() not in ("0", "false", "False")
    provider = os.getenv("EXPLAIN_PROVIDER", "disabled").strip()
    timeout_s = int(os.getenv("EXPLAIN_TIMEOUT_S", "10").strip())

    return ExplanationEngine(ExplainConfig(enabled=enabled, provider=provider, timeout_s=timeout_s))