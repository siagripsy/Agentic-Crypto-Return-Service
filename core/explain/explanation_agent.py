from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any, Dict, Literal

from core.explain.fallback import (
    explain_crypto_return_service_fallback,
    explain_forecast_fallback,
    explain_portfolio_fallback,
)
from core.explain.llm_client import LLMConfig, build_llm_client


ExplainTarget = Literal["forecast", "portfolio", "crypto_return_service"]


SYSTEM_PROMPT_DEFAULT = """You explain crypto forecast and portfolio outputs conservatively.

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


SYSTEM_PROMPT_CRYPTO_RETURN_SERVICE = """You explain combined crypto regime matching, scenario engine, and portfolio outputs conservatively.

Rules:
- Return STRICT JSON only.
- No markdown.
- No code fences.
- No extra text before or after the JSON.
- Use only values present in the payload.
- Do not invent unavailable fields.
- Do not give financial advice.
- Do not recommend buying, selling, or holding.
- Keep the language easy to read.
- Mention uncertainty where relevant.
- Each bullet must be one sentence.
- Make the explanation materially detailed and decision-useful without becoming verbose.
- Keep overall_summary to 4 to 6 sentences with concrete comparisons across assets when possible.
- Each section headline should contain a specific takeaway, not a generic label.
- Each section must have 5 bullets.
- Bullets should mention concrete signals such as probabilities, median outcomes, ranges, drawdowns, CVaR, weight concentration, or uncertainty when those values exist.
- If a value is unavailable, explain the gap rather than inventing it.

Return exactly this schema:
{
  "mode": "llm",
  "disclaimer": "<string>",
  "overall_summary": "<4 to 6 sentences>",
  "sections": {
    "regime_matching": {
      "headline": "<string>",
      "bullets": ["<string>", "<string>", "<string>", "<string>", "<string>"]
    },
    "scenario_engine": {
      "headline": "<string>",
      "bullets": ["<string>", "<string>", "<string>", "<string>", "<string>"]
    },
    "risk_portfolio": {
      "headline": "<string>",
      "bullets": ["<string>", "<string>", "<string>", "<string>", "<string>"]
    }
  }
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


def _compact_crypto_return_service_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    regime_matching = payload.get("regime_matching") or {}
    scenario_engine = payload.get("scenario_engine") or {}
    risks = payload.get("risks") or {}
    portfolio = payload.get("portfolio") or {}

    compact_assets: Dict[str, Any] = {}
    all_assets = set(regime_matching.keys()) | set(scenario_engine.keys()) | set(risks.keys())
    for asset in sorted(all_assets):
        regime_block = regime_matching.get(asset) or {}
        regime_summary = regime_block.get("summary") or {}
        profit_analysis = regime_summary.get("profit_analysis") or {}
        loss_analysis = regime_summary.get("loss_analysis") or {}
        drawdown_analysis = regime_summary.get("drawdown_analysis") or {}
        top_matches = []
        for match in (regime_block.get("matches") or [])[:3]:
            top_matches.append(
                {
                    "rank": match.get("rank"),
                    "window_start_date": match.get("window_start_date"),
                    "window_end_date": match.get("window_end_date"),
                    "forward_end_date": match.get("forward_end_date"),
                    "similarity": match.get("similarity"),
                    "profit_pct": match.get("profit_pct"),
                    "max_drawdown_pct": match.get("max_drawdown_pct"),
                }
            )

        scenario_summary = (scenario_engine.get(asset) or {}).get("summary") or {}
        risk_block = risks.get(asset) or {}

        compact_assets[asset] = {
            "regime_matching": {
                "prob_profit": regime_summary.get("prob_profit"),
                "mean_profit": profit_analysis.get("mean_profit"),
                "mean_loss": loss_analysis.get("mean_loss"),
                "mean_max_drawdown": drawdown_analysis.get("mean_max_drawdown"),
                "top_matches": top_matches,
            },
            "scenario_engine": {
                "start_price": scenario_summary.get("start_price"),
                "terminal_mean": scenario_summary.get("terminal_mean"),
                "terminal_median": scenario_summary.get("terminal_median"),
                "terminal_p05": scenario_summary.get("terminal_p05"),
                "terminal_p95": scenario_summary.get("terminal_p95"),
            },
            "risk_metrics": {
                "var": risk_block.get("var"),
                "cvar": risk_block.get("cvar"),
                "max_drawdown_est": risk_block.get("max_drawdown_est"),
                "prob_profit": (risk_block.get("tail_metrics") or {}).get("prob_profit"),
                "expected_return_mean": ((risk_block.get("tail_metrics") or {}).get("horizon_return_summary") or {}).get("mean"),
            },
        }

    return {
        "input": {
            "capital": (payload.get("input") or {}).get("capital"),
            "horizon_days": (payload.get("input") or {}).get("horizon_days"),
            "n_scenarios": (payload.get("input") or {}).get("n_scenarios"),
            "risk_tolerance": (payload.get("input") or {}).get("risk_tolerance"),
        },
        "assets": compact_assets,
        "portfolio": {
            "weights": portfolio.get("weights"),
            "details": portfolio.get("details"),
            "portfolio_expected_return": portfolio.get("portfolio_expected_return"),
            "portfolio_cvar": portfolio.get("portfolio_cvar"),
            "portfolio_max_drawdown_est": portfolio.get("portfolio_max_drawdown_est"),
        },
    }


def _compact_payload(target: ExplainTarget, payload: Dict[str, Any]) -> Dict[str, Any]:
    if target == "crypto_return_service":
        return _compact_crypto_return_service_payload(payload)
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
                system=SYSTEM_PROMPT_CRYPTO_RETURN_SERVICE if target == "crypto_return_service" else SYSTEM_PROMPT_DEFAULT,
                user=f"Target={target}\nPayload={compact_json}",
                timeout_s=self.cfg.timeout_s,
            )
            print(f"[explain] llm raw output={out}")

            if not isinstance(out, dict):
                raise ValueError("LLM output not a dict")

            out["mode"] = "llm"
            if target == "crypto_return_service":
                out.setdefault("disclaimer", _default_disclaimer())
                out.setdefault("overall_summary", "")
                out.setdefault(
                    "sections",
                    {
                        "regime_matching": {"headline": "", "bullets": []},
                        "scenario_engine": {"headline": "", "bullets": []},
                        "risk_portfolio": {"headline": "", "bullets": []},
                    },
                )
            else:
                out.setdefault("disclaimer", _default_disclaimer())
                out.setdefault("bullets", [])
                out.setdefault("narrative", "")
            return out

        except Exception as e:
            print(f"[explain] llm exception: {type(e).__name__}: {e}")
            return self._fallback(target, payload)

    def _fallback(self, target: ExplainTarget, payload: Dict[str, Any]) -> Dict[str, Any]:
        if target == "crypto_return_service":
            return explain_crypto_return_service_fallback(payload)
        if target == "portfolio":
            return explain_portfolio_fallback(payload)
        return explain_forecast_fallback(payload)


def load_explanation_engine_from_env() -> ExplanationEngine:
    enabled = os.getenv("EXPLAIN_ENABLED", "1").strip() not in ("0", "false", "False")
    provider = os.getenv("EXPLAIN_PROVIDER", "disabled").strip()
    timeout_s = int(os.getenv("EXPLAIN_TIMEOUT_S", "10").strip())

    return ExplanationEngine(ExplainConfig(enabled=enabled, provider=provider, timeout_s=timeout_s))
