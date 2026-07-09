import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Activity,
  ExternalLink,
} from "lucide-react";
import {
  getCompanies,
  getCompanyRisk,
  getCompanyNews,
  getStockQuote,
  getStockPriceHistory,
  type CompanyRiskDetail,
  type StockQuote,
  type NewsItem,
  type PricePoint,
} from "../api/api";
import { PriceChart } from "../components/PriceChart";
import { ExportReport } from "../components/ExportReport";
import { CompanyRiskGauge } from "../components/CompanyRiskGauge";
import { RiskRadarChart } from "../components/RiskRadarChart";
import { RiskMatrixGrid } from "../components/RiskMatrixGrid";
import { ScenarioSimulator } from "../components/ScenarioSimulator";

const TIME_RANGES = ["1d", "1w", "1m", "3m", "6m", "1y", "5y", "max"] as const;

function formatMarketCap(val: number | null): string {
  if (val == null) return "—";
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
  return `$${val.toLocaleString()}`;
}

function formatNumber(val: number | null | undefined, decimals = 2): string {
  if (val == null) return "—";
  return val.toFixed(decimals);
}

function formatVolume(vol: number | null | undefined): string {
  if (vol == null) return "—";
  if (vol >= 1e9) return `${(vol / 1e9).toFixed(1)}B`;
  if (vol >= 1e6) return `${(vol / 1e6).toFixed(1)}M`;
  if (vol >= 1e3) return `${(vol / 1e3).toFixed(1)}K`;
  return String(vol);
}

export function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>();
  const navigate = useNavigate();

  const [quote, setQuote] = useState<StockQuote | null>(null);
  const [company, setCompany] = useState<CompanyRiskDetail | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [pricePoints, setPricePoints] = useState<PricePoint[]>([]);
  const [selectedRange, setSelectedRange] = useState<string>("1m");
  const [loadingQuote, setLoadingQuote] = useState(true);
  const [loadingChart, setLoadingChart] = useState(true);
  const [loadingRisk, setLoadingRisk] = useState(true);

  const tickerUpper = ticker?.toUpperCase() ?? "";

  // Fetch quote
  useEffect(() => {
    if (!tickerUpper) return;
    setLoadingQuote(true);
    getStockQuote(tickerUpper)
      .then(setQuote)
      .catch(() => setQuote(null))
      .finally(() => setLoadingQuote(false));
  }, [tickerUpper]);

  // Fetch price history
  useEffect(() => {
    if (!tickerUpper) return;
    setLoadingChart(true);
    getStockPriceHistory(tickerUpper, selectedRange)
      .then((r) => setPricePoints(r.points))
      .catch(() => setPricePoints([]))
      .finally(() => setLoadingChart(false));
  }, [tickerUpper, selectedRange]);

  // Fetch risk detail + news
  useEffect(() => {
    if (!tickerUpper) return;
    setLoadingRisk(true);

    // First get company list to find the ID
    getCompanies()
      .then((companies) => {
        const match = companies.find((c) => c.ticker.toUpperCase() === tickerUpper);
        if (match) {
          return getCompanyRisk(match.id).then((detail) => {
            setCompany(detail);
            return getCompanyNews(match.id)
              .then(setNews)
              .catch(() => setNews([]));
          });
        } else {
          // Try by ticker directly (backend supports it)
          return getCompanyRisk(tickerUpper).then((detail) => {
            setCompany(detail);
            return getCompanyNews(detail.id)
              .then(setNews)
              .catch(() => setNews([]));
          });
        }
      })
      .catch(() => {
        setCompany(null);
        setNews([]);
      })
      .finally(() => setLoadingRisk(false));
  }, [tickerUpper]);

  const isPositive = (quote?.day_change ?? 0) >= 0;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 px-6 py-3 border-b border-navy-700 bg-navy-950">
        <div className="max-w-screen-2xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/")}
              className="p-1.5 rounded-lg hover:bg-navy-800 transition-colors"
            >
              <ArrowLeft size={18} className="text-[#1C1C1C]" />
            </button>
            <div className="w-8 h-8 rounded-md bg-electric-500/10 border border-electric-500/30 flex items-center justify-center">
              <BarChart3 size={16} className="text-electric-500" />
            </div>
            <div>
              <h1 className="text-sm font-serif font-bold text-[#1C1C1C]">Vantage Risk</h1>
              <p className="text-xs text-stone-600 font-sans">Stock Analysis</p>
            </div>
          </div>

          {/* Export Report */}
          {company && (
            <ExportReport company={company} quote={quote} news={news} />
          )}
        </div>
      </header>

      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-6 py-6 space-y-6">
        {/* ── Price Header ──────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-6"
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <span className="ticker-label text-base">{tickerUpper}</span>
                {company?.altman_tier && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                    badge-${(company.altman_tier ?? "grey").toLowerCase().replace(" ", "")}`}>
                    {company.altman_tier}
                  </span>
                )}
                {company?.risk_tier && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                    ${company.risk_tier === "Low" ? "badge-low" :
                      company.risk_tier === "Medium" ? "badge-medium" :
                      company.risk_tier === "High" ? "badge-high" : "badge-critical"}`}>
                    {company.risk_tier} Risk
                  </span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-[#1C1C1C]">
                {quote?.name ?? company?.name ?? tickerUpper}
              </h2>
              <p className="text-xs text-stone-500 mt-0.5">
                {company?.sector ?? ""} {company?.sector && "·"} {quote?.currency ?? "USD"}
              </p>
            </div>

            {/* Price Display */}
            {!loadingQuote && quote && (
              <div className="text-right">
                <p className="text-3xl font-bold font-mono text-[#1C1C1C]">
                  ${quote.price.toFixed(2)}
                </p>
                <div className="flex items-center justify-end gap-1.5 mt-1">
                  {isPositive ? (
                    <TrendingUp size={14} className="text-emerald-600" />
                  ) : (
                    <TrendingDown size={14} className="text-red-600" />
                  )}
                  <span className={`text-sm font-mono font-semibold ${isPositive ? "text-emerald-600" : "text-red-600"}`}>
                    {isPositive ? "+" : ""}{quote.day_change.toFixed(2)}
                    ({isPositive ? "+" : ""}{quote.day_change_pct.toFixed(2)}%)
                  </span>
                </div>
              </div>
            )}

            {loadingQuote && (
              <div className="w-6 h-6 rounded-full border-2 border-stone-300 border-t-electric-500 animate-spin" />
            )}
          </div>
        </motion.div>

        {/* ── Time Range Selector + Chart ────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-6"
        >
          {/* Time Range Pills */}
          <div className="flex items-center justify-between mb-4">
            <p className="section-title mb-0">Price Chart</p>
            <div className="flex gap-1">
              {TIME_RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => setSelectedRange(r)}
                  className={`px-3 py-1 text-xs font-mono font-semibold rounded-md transition-all
                    ${selectedRange === r
                      ? "bg-electric-500 text-white"
                      : "text-stone-500 hover:bg-navy-800 hover:text-[#1C1C1C]"
                    }`}
                >
                  {r.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {loadingChart ? (
            <div className="flex items-center justify-center h-[360px]">
              <div className="w-8 h-8 rounded-full border-2 border-stone-300 border-t-electric-500 animate-spin" />
            </div>
          ) : (
            <PriceChart points={pricePoints} range={selectedRange} />
          )}
        </motion.div>

        {/* ── Key Statistics Grid ────────────────────────────────── */}
        {quote && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card p-6"
          >
            <p className="section-title mb-4">Key Statistics</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {[
                { label: "Open", value: `$${formatNumber(quote.open)}` },
                { label: "High", value: `$${formatNumber(quote.high)}` },
                { label: "Low", value: `$${formatNumber(quote.low)}` },
                { label: "Close", value: `$${formatNumber(quote.close)}` },
                { label: "Volume", value: formatVolume(quote.volume) },
                { label: "Market Cap", value: formatMarketCap(quote.market_cap) },
                { label: "P/E Ratio", value: formatNumber(quote.pe_ratio) },
                { label: "Dividend Yield", value: quote.dividend_yield != null ? `${(quote.dividend_yield * 100).toFixed(2)}%` : "—" },
                { label: "52W High", value: `$${formatNumber(quote.week52_high)}` },
                { label: "52W Low", value: `$${formatNumber(quote.week52_low)}` },
                { label: "Beta", value: formatNumber(quote.beta) },
                { label: "Avg Volume", value: formatVolume(quote.avg_volume) },
              ].map((stat) => (
                <div key={stat.label} className="rounded-lg p-3 border border-navy-700 bg-navy-900">
                  <p className="text-[10px] text-stone-500 font-mono uppercase tracking-wider mb-1">{stat.label}</p>
                  <p className="text-sm font-bold font-mono text-[#1C1C1C]">{stat.value}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── Risk Analysis Section ─────────────────────────────── */}
        {company && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="space-y-6"
          >
            {/* Gauge + Radar */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass-card p-5 flex flex-col items-center justify-center">
                <p className="section-title mb-3">Composite Risk Score</p>
                <CompanyRiskGauge
                  score={company.composite_risk_score ?? 50}
                  tier={company.risk_tier}
                  size={160}
                  label={company.ticker}
                />
                <div className="mt-4 space-y-1.5 w-full max-w-xs">
                  {[
                    { label: "Altman Z-Score", value: company.altman_z?.toFixed(2) ?? "—" },
                    { label: "Prob. of Default", value: company.prob_of_default != null ? `${(company.prob_of_default * 100).toFixed(2)}%` : "—" },
                    { label: "Distance-to-Default", value: company.distance_to_default?.toFixed(3) ?? "—" },
                  ].map((m) => (
                    <div key={m.label} className="flex justify-between text-xs">
                      <span className="text-stone-500">{m.label}</span>
                      <span className="font-mono text-[#1C1C1C] font-semibold">{m.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card p-5">
                <p className="section-title mb-2">Risk Dimensions</p>
                <RiskRadarChart company={company} />
              </div>
            </div>

            {/* SHAP Drivers */}
            {(company.top_risk_driver_1 || company.top_risk_driver_2) && (
              <div className="glass-card p-5">
                <p className="section-title mb-3">Risk Drivers (SHAP Attribution)</p>
                <div className="space-y-2">
                  {[company.top_risk_driver_1, company.top_risk_driver_2, company.top_risk_driver_3]
                    .filter(Boolean)
                    .map((driver, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -8 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="flex items-start gap-3 p-3 rounded-lg bg-navy-900 border border-navy-700"
                      >
                        <span className="flex-shrink-0 w-5 h-5 rounded-full bg-electric-500/20 text-electric-500 flex items-center justify-center text-xs font-bold">
                          {i + 1}
                        </span>
                        <p className="text-xs text-[#1C1C1C] leading-relaxed">{driver}</p>
                      </motion.div>
                    ))}
                </div>
              </div>
            )}

            {/* Risk Matrix */}
            <div className="glass-card p-5">
              <p className="section-title mb-3">Credit Risk Matrix Breakdown</p>
              <RiskMatrixGrid company={company} />
            </div>

            {/* Scenario Simulator */}
            <div className="glass-card p-5">
              <p className="section-title mb-3">Rate Shock Scenario</p>
              <ScenarioSimulator company={company} />
            </div>
          </motion.div>
        )}

        {loadingRisk && !company && (
          <div className="glass-card p-12 flex items-center justify-center">
            <div className="w-8 h-8 rounded-full border-2 border-stone-300 border-t-electric-500 animate-spin" />
          </div>
        )}

        {/* ── News Feed ─────────────────────────────────────────── */}
        {news.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-card p-6"
          >
            <p className="section-title mb-4">Latest News</p>
            <div className="space-y-3">
              {news.map((item, idx) => (
                <Link
                  key={idx}
                  to={`/news/${tickerUpper}/${idx}`}
                  state={{ newsItem: item, companyName: company?.name }}
                  className="block p-4 rounded-xl bg-navy-900 border border-navy-700 hover:border-stone-400 hover:shadow-card-hover transition-all duration-200 group"
                >
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <span className="text-[10px] text-stone-500 font-mono">{item.publisher}</span>
                    <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase
                      ${item.sentiment === "Bullish" ? "badge-low" :
                        item.sentiment === "Bearish" ? "badge-high" : "badge-medium"}`}>
                      {item.sentiment} ({item.score > 0 ? "+" : ""}{item.score})
                    </span>
                  </div>
                  <h4 className="text-xs font-bold text-[#E60000] leading-snug group-hover:text-electric-600 transition-colors">
                    {item.headline}
                  </h4>
                  {item.summary && (
                    <p className="text-xs text-stone-500 leading-relaxed mt-1.5 line-clamp-2">
                      {item.summary}
                    </p>
                  )}
                  <div className="flex items-center gap-1 mt-2 text-[11px] font-semibold text-electric-500 group-hover:text-electric-600">
                    Read Full Article
                    <ExternalLink size={10} />
                  </div>
                </Link>
              ))}
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
