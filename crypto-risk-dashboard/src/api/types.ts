export type EngineType =
  | "fast_regime_fixed"
  | "walkforward_ml"
  | "regime_similarity"
  | "ensemble";

export type RiskLevel = "low" | "medium" | "high";
export type ReturnFormat = "log" | "simple" | "both";

export type ExplanationMode = "fallback" | "llm";

export interface HorizonRequest {
  symbol: string;
  start_date: string;
  end_date?: string | null;
  horizon_days?: number | null;

  engine: EngineType;
  n_scenarios: number;

  alpha: number;
  risk_level?: RiskLevel | null;
  alphas?: number[] | null;

  seed: number;
  return_format: ReturnFormat;
  timeout_seconds?: number | null;

  include_explanation: boolean;
  explanation_mode: ExplanationMode;
}

export interface HorizonResponse {
  symbol: string;
  start_date: string;
  end_date: string;
  horizon_days: number;
  n_scenarios: number;
  alpha: number;
  engine: string;
  assumptions: Record<string, any>;

  summary?: Record<string, number> | null;
  risk?: Record<string, number> | null;

  metrics?: Record<string, any> | null;
  risk_curve_metrics?: Record<string, any> | null;

  explanation?: Record<string, any> | null;
}

export interface MultiHorizonRequest {
  symbols: string[];
  start_date: string;
  end_date?: string | null;
  horizon_days?: number | null;

  engine: EngineType;
  n_scenarios: number;

  alpha: number;
  risk_level?: RiskLevel | null;
  alphas?: number[] | null;

  seed: number;
  return_format: ReturnFormat;
  timeout_seconds?: number | null;

  include_explanation: boolean;
  explanation_mode: ExplanationMode;
}

export interface MultiHorizonResponse {
  results: HorizonResponse[];
}

export type PortfolioEngine = "walkforward_ml" | "regime_similarity" | "ensemble";

export interface PortfolioRequest {
  symbols: string[];
  start_date: string;
  horizon_days: number;

  engine: PortfolioEngine;
  n_scenarios: number;
  seed: number;

  confidence_levels: number[];
  user_risk_tolerance: number;
  top_k: number;
  max_weight: number;
  min_weight: number;
  allow_cash: boolean;

  timeout_seconds?: number | null;

  include_explanation: boolean;
  explanation_mode: ExplanationMode;
}

export interface PortfolioResponse {
  assumptions: Record<string, any>;
  risks: Record<string, any>;
  portfolio: Record<string, any>;
  explanation?: Record<string, any> | null;
}