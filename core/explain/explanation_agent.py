from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any, Dict, Literal

from core.explain.fallback import explain_forecast_fallback, explain_portfolio_fallback
from core.explain.llm_client import LLMConfig, build_llm_client


ExplainTarget = Literal["forecast", "portfolio"]


SYSTEM_PROMPT = """You explain crypto forecast and portfolio outputs conservatively.

Rules:
- Return STRICT JSON only.
- Do not add any intro text, markdown, code fences, or text before or after the JSON.
- Keep it short.
- Use exactly 4-5 bullets.
- Each bullet must be one sentence.
- Narrative must be 2 sentences maximum.
- Do not use markdown.
- Do not invent data.
- Do not give financial advice.

Schema:
{
  "mode": "llm",
  "disclaimer": "<string>",
  "bullets": ["<string>", "..."],
  "narrative": "<string>"
}
"""


def _default_disclaimer() -> str:
    return (
        "This explanation is informational only and not financial advice. "
        "Crypto forecasts are uncertain and based on model assumptions and simulated scenarios."
    )


def _pick(d: Dict[str, Any], keys: list[str]) -> Dict[str, Any]:
    return {k: d.get(k) for k in keys if k in d}


def _compact_forecast_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    metrics = payload.get("metrics") or {}
    block = metrics.get("simple") or metrics.get("log") or {}

    hrs = block.get("horizon_return_summary") or {}
    tps = block.get("terminal_price_summary") or {}
    ret_risk = block.get("VaR_CVaR_horizon_return") or {}
    dd_risk = block.get("VaR_CVaR_max_drawdown") or {}
    mdd = block.get("max_drawdown_summary") or {}

    return {
        "symbol": payload.get("symbol"),
        "engine": payload.get("engine"),
        "horizon_days": payload.get("horizon_days"),
        "n_scenarios": payload.get("n_scenarios"),
        "alpha": payload.get("alpha"),
        "return_summary": _pick(hrs, ["mean", "median", "p05", "p95"]),
        "terminal_price_summary": _pick(tps, ["mean", "median", "p05", "p95"]),
        "prob_profit": block.get("prob_profit"),
        "prob_loss": block.get("prob_loss"),
        "var_cvar_return": _pick(ret_risk, ["VaR", "CVaR"]),
        "max_drawdown_summary": _pick(mdd, ["mean", "median", "p05", "p95"]),
        "var_cvar_drawdown": _pick(dd_risk, ["VaR", "CVaR"]),
    }


def _compact_portfolio_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    portfolio = payload.get("portfolio") or {}
    risks = payload.get("risks") or {}

    compact_risks: Dict[str, Any] = {}
    for sym, rr in list(risks.items())[:10]:
        compact_risks[sym] = {
            "var": rr.get("var"),
            "cvar": rr.get("cvar"),
            "max_drawdown_est": rr.get("max_drawdown_est"),
        }

    return {
        "assumptions": payload.get("assumptions"),
        "portfolio": {
            "weights": portfolio.get("weights"),
            "details": portfolio.get("details"),
            "portfolio_expected_return": portfolio.get("portfolio_expected_return"),
            "portfolio_cvar": portfolio.get("portfolio_cvar"),
            "portfolio_max_drawdown_est": portfolio.get("portfolio_max_drawdown_est"),
        },
        "risks": compact_risks,
    }


def _compact_payload(target: ExplainTarget, payload: Dict[str, Any]) -> Dict[str, Any]:
    if target == "portfolio":
        return _compact_portfolio_payload(payload)
    return _compact_forecast_payload(payload)


@dataclass
class ExplainConfig:
    enabled: bool = True
    provider: str = "disabled"
    timeout_s: int = 10


class ExplanationEngine:
    def __init__(self, cfg: ExplainConfig):
        self.cfg = cfg
        llm_cfg = LLMConfig(
            provider=cfg.provider,
            default_timeout_s=cfg.timeout_s,
        )
        self._client = build_llm_client(llm_cfg)
        print(
            f"[explain] enabled={cfg.enabled} provider={cfg.provider} "
            f"client_loaded={self._client is not None}"
        )

    async def explain(self, *, target: ExplainTarget, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.cfg.enabled:
            print("[explain] disabled -> fallback")
            return self._fallback(target, payload)

        if self._client is None:
            print("[explain] client is None -> fallback")
            return self._fallback(target, payload)

        compact_payload = _compact_payload(target, payload)
        compact_json = json.dumps(compact_payload, separators=(",", ":"), ensure_ascii=False)

        try:
            print(f"[explain] calling llm target={target} prompt_chars={len(compact_json)}")
            out = await self._client.generate_json(
                system=SYSTEM_PROMPT,
                user=f"Target={target}\nPayload={compact_json}",
                timeout_s=self.cfg.timeout_s,
            )
            print(f"[explain] llm raw output={out}")

            if not isinstance(out, dict):
                raise ValueError("LLM output not a dict")

            out["mode"] = "llm"
            out.setdefault("disclaimer", _default_disclaimer())
            out.setdefault("bullets", [])
            out.setdefault("narrative", "")
            return out

        except Exception as e:
            print(f"[explain] llm exception: {type(e).__name__}: {e}")
            return self._fallback(target, payload)

    def _fallback(self, target: ExplainTarget, payload: Dict[str, Any]) -> Dict[str, Any]:
        if target == "portfolio":
            return explain_portfolio_fallback(payload)
        return explain_forecast_fallback(payload)


def load_explanation_engine_from_env() -> ExplanationEngine:
    enabled = os.getenv("EXPLAIN_ENABLED", "1").strip() not in ("0", "false", "False")
    provider = os.getenv("EXPLAIN_PROVIDER", "disabled").strip()
    timeout_s = int(os.getenv("EXPLAIN_TIMEOUT_S", "10").strip())

    return ExplanationEngine(ExplainConfig(enabled=enabled, provider=provider, timeout_s=timeout_s))