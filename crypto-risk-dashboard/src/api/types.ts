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
  assumptions: Record<string, unknown>;
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
  assumptions: Record<string, unknown>;
  risks: Record<string, unknown>;
  portfolio: Record<string, unknown>;
  explanation?: Record<string, unknown> | null;
}

export interface AssetOption {
  symbol: string;
  yahoo_ticker: string;
}

export interface AssetOptionsResponse {
  items: AssetOption[];
}

export interface CryptoReturnServiceRequest {
  capital: number;
  assets: Record<string, number>;
  horizon_days: number;
  n_scenarios: number;
  risk_tolerance: number;
  include_explanation: boolean;
  explanation_mode: ExplanationMode;
}

export interface RegimeMatch {
  rank: number;
  similarity: number;
  window_start_date: string;
  window_end_date: string;
  forward_end_date: string;
  profit_pct: number;
  max_drawdown_pct: number;
}

export interface RegimeMatchingBlock {
  current_window?: Record<string, unknown>;
  matches: RegimeMatch[];
  summary?: {
    n_evaluated?: number;
    prob_profit?: number;
    profit_analysis?: {
      count?: number;
      mean_profit?: number | null;
      max_profit?: number | null;
      min_profit?: number | null;
    };
    loss_analysis?: {
      count?: number;
      mean_loss?: number | null;
      worst_loss?: number | null;
      smallest_loss?: number | null;
    };
    drawdown_analysis?: {
      mean_max_drawdown?: number | null;
      worst_max_drawdown?: number | null;
    };
  };
  used_cached_model?: boolean;
}

export interface ScenarioSummary {
  start_price: number;
  horizon_days: number;
  n_scenarios: number;
  terminal_mean: number;
  terminal_median: number;
  terminal_p05: number;
  terminal_p50: number;
  terminal_p95: number;
}

export interface ScenarioEngineBlock {
  asset: string;
  distribution?: Record<string, unknown>;
  summary: ScenarioSummary;
  paths: number[][];
  metadata?: Record<string, unknown>;
  metrics?: Record<string, any>;
}

export interface RiskReport {
  symbol: string;
  horizon_days: number;
  var: Record<string, number>;
  cvar: Record<string, number>;
  max_drawdown_est?: number | null;
  tail_metrics?: Record<string, any>;
  notes?: string[];
}

export interface PortfolioDetail {
  symbol: string;
  weight: number;
  expected_return_mean: number;
  prob_profit: number;
  cvar: number;
  max_drawdown_est: number;
  score: number;
  notes?: string[];
}

export interface PortfolioResult {
  weights: Record<string, number>;
  details: PortfolioDetail[];
  portfolio_expected_return?: number | null;
  portfolio_cvar?: number | null;
  portfolio_max_drawdown_est?: number | null;
  metadata?: Record<string, unknown>;
}

export interface ExplanationSection {
  headline: string;
  bullets: string[];
}

export interface CryptoServiceExplanation {
  mode: "llm" | "fallback";
  disclaimer: string;
  overall_summary: string;
  sections: {
    regime_matching: ExplanationSection;
    scenario_engine: ExplanationSection;
    risk_portfolio: ExplanationSection;
  };
}

export interface CryptoReturnServiceResponse {
  input?: CryptoReturnServiceRequest;
  regime_matching: Record<string, RegimeMatchingBlock>;
  scenario_engine: Record<string, ScenarioEngineBlock>;
  risks: Record<string, RiskReport>;
  portfolio: PortfolioResult;
  explanation?: CryptoServiceExplanation | null;
}
