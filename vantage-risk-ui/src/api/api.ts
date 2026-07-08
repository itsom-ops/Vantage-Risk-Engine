import axios from "axios";

const BASE_URL = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
});

// Attach X-Response-Time from response headers to the response data
api.interceptors.response.use((response) => {
  const serverMs = response.headers["x-response-time-ms"];
  if (serverMs) {
    (response as any)._serverMs = parseFloat(serverMs);
  }
  return response;
});

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

export interface CompanySummary {
  id: string;
  ticker: string;
  name: string;
  sector: string | null;
  country: string | null;
  altman_z: number | null;
  altman_tier: "Safe" | "Grey Zone" | "Distress" | null;
  composite_risk_score: number | null;
  risk_tier: "Low" | "Medium" | "High" | "Critical" | null;
  prob_of_default: number | null;
  period: string | null;
}

export interface SHAPDriver {
  feature: string;
  raw_value: number;
  shap_value: number;
  direction: string;
  plain_text: string;
}

export interface CompanyRiskDetail extends CompanySummary {
  x1_working_cap_ratio: number | null;
  x2_retained_earn_ratio: number | null;
  x3_ebit_ratio: number | null;
  x4_equity_debt_ratio: number | null;
  x5_sales_ratio: number | null;
  distance_to_default: number | null;
  shap_drivers: SHAPDriver[];
  top_risk_driver_1: string | null;
  top_risk_driver_2: string | null;
  top_risk_driver_3: string | null;
  computed_at: string | null;
  response_time_ms: number | null;
}

export interface PortfolioRiskResponse {
  n_companies: number;
  var_95: number;
  cvar_95: number;
  avg_composite_score: number;
  worst_company_ticker: string | null;
  worst_company_score: number | null;
  risk_distribution: Record<string, number>;
}

export interface ScenarioResponse {
  company_id: string;
  ticker: string;
  rate_shock_bps: number;
  base_altman_z: number | null;
  stressed_altman_z: number | null;
  base_tier: string | null;
  stressed_tier: string | null;
  base_interest_coverage: number | null;
  stressed_interest_coverage: number | null;
  tier_changed: boolean;
  narrative: string;
}

export interface InsightResponse {
  company_id: string;
  ticker: string;
  query: string;
  narrative: string;
  recommendation: "Monitor" | "Flag for review" | "Low concern";
  sources_used: number;
  response_time_ms: number | null;
}

export interface LatencyStats {
  tag: string;
  n_requests: number;
  avg_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
}

export interface LatencyStatsResponse {
  stats: LatencyStats[];
  improvement_pct: number | null;
  optimized_p95_ms: number | null;
}

// ─────────────────────────────────────────────────────────────────────────────
export interface NewsItem {
  headline: string;
  publisher: string;
  link: string;
  time: string;
  sentiment: "Bullish" | "Neutral" | "Bearish";
  score: number;
  effect: string;
  summary?: string;
}

export interface StressedCompanyInfo {
  ticker: string;
  base_score: number;
  stressed_score: number;
  net_sentiment: number;
  status: "Stressed" | "Stable";
}

export interface SentimentPortfolioResponse {
  base_var_95: number;
  base_cvar_95: number;
  sentiment_var_95: number;
  sentiment_cvar_95: number;
  net_portfolio_sentiment: number;
  stressed_companies: StressedCompanyInfo[];
}

export interface RiskLeaf {
  title: string;
  value: string;
  severity: "Low" | "Medium" | "High";
  explanation: string;
}

export interface RiskMatrixResponse {
  credit_risks: RiskLeaf[];
  liquidity_risks: RiskLeaf[];
  governance_risks: RiskLeaf[];
  market_risks: RiskLeaf[];
  external_risks: RiskLeaf[];
  legal_compliance: RiskLeaf[];
}

// API calls
// ─────────────────────────────────────────────────────────────────────────────

export const getCompanies = () =>
  api.get<CompanySummary[]>("/companies").then((r) => r.data);

export const getCompanyRisk = (id: string) =>
  api.get<CompanyRiskDetail>(`/companies/${id}/risk`).then((r) => r.data);

export const getPortfolioRisk = (company_ids: string[]) =>
  api.post<PortfolioRiskResponse>("/portfolio/risk", { company_ids }).then((r) => r.data);

export const runScenario = (company_id: string, rate_shock_bps: number) =>
  api.post<ScenarioResponse>("/scenario", { company_id, rate_shock_bps }).then((r) => r.data);

export const getInsight = (company_id: string, query: string) =>
  api.post<InsightResponse>("/insight", { company_id, query }).then((r) => r.data);

export const getLatencyStats = () =>
  api.get<LatencyStatsResponse>("/latency-stats").then((r) => r.data);

export const getCompanyNews = (id: string) =>
  api.get<NewsItem[]>(`/companies/${id}/news`).then((r) => r.data);

export const getSentimentPortfolioRisk = (company_ids: string[], severity_multiplier: number) =>
  api.post<SentimentPortfolioResponse>("/portfolio/sentiment-adjusted-risk", {
    company_ids,
    severity_multiplier,
  }).then((r) => r.data);

export const getCompanyNewsCorrelation = (id: string) =>
  api.get<{ correlation_summary: string }>(`/companies/${id}/news-correlation`).then((r) => r.data);

export const getCompanyRiskMatrix = (id: string) =>
  api.get<RiskMatrixResponse>(`/companies/${id}/risk-matrix`).then((r) => r.data);
