import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  getCompanies,
  getCompanyRisk,
  getInsight,
  getLatencyStats,
  getCompanyNews,
  getSentimentPortfolioRisk,
  type CompanySummary,
  type CompanyRiskDetail,
  type InsightResponse,
  type LatencyStatsResponse,
  type NewsItem,
  type SentimentPortfolioResponse,
} from "../api/api";
import { CompanyRiskGauge } from "../components/CompanyRiskGauge";
import { RiskRadarChart } from "../components/RiskRadarChart";
import { PortfolioHeatmap } from "../components/PortfolioHeatmap";
import { ScenarioSimulator } from "../components/ScenarioSimulator";
import { LatencyTicker } from "../components/LatencyTicker";
import { RiskMatrixGrid } from "../components/RiskMatrixGrid";
import {
  Search, ChevronRight, BarChart3, Shield, AlertTriangle,
  TrendingUp, Layers, Zap, RefreshCw, MessageSquare, Plus, Activity
} from "lucide-react";

// Typewriter hook
function useTypewriter(text: string, speed = 18) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    setDisplayed("");
    if (!text) return;
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(timer);
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed]);
  return displayed;
}

type ActivePanel = "overview" | "detail" | "portfolio" | "benchmark" | "news";

export function Dashboard() {
  const [companies, setCompanies] = useState<CompanySummary[]>([]);
  const [selected, setSelected] = useState<CompanyRiskDetail | null>(null);
  const [loadingCompanies, setLoadingCompanies] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [activePanel, setActivePanel] = useState<ActivePanel>("overview");

  // Query bar state
  const [query, setQuery] = useState("");
  const [queryLoading, setQueryLoading] = useState(false);
  const [insight, setInsight] = useState<InsightResponse | null>(null);
  const [latencyStats, setLatencyStats] = useState<LatencyStatsResponse | null>(null);

  // News and Sentiment state
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loadingNews, setLoadingNews] = useState(false);
  const [severity, setSeverity] = useState(1.0);
  const [sentimentRisk, setSentimentRisk] = useState<SentimentPortfolioResponse | null>(null);
  const [loadingSentimentRisk, setLoadingSentimentRisk] = useState(false);

  // Ticker search/ingest state
  const [tickerInput, setTickerInput] = useState("");
  const [tickerLoading, setTickerLoading] = useState(false);

  const displayedNarrative = useTypewriter(insight?.narrative ?? "");

  // Poll latency statistics
  useEffect(() => {
    const fetchStats = () => {
      getLatencyStats()
        .then(setLatencyStats)
        .catch(() => {});
    };
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch news when selected company changes
  useEffect(() => {
    if (selected) {
      setLoadingNews(true);
      getCompanyNews(selected.id)
        .then(setNews)
        .catch(() => setNews([]))
        .finally(() => setLoadingNews(false));
    }
  }, [selected]);

  // Fetch sentiment portfolio risk on multiplier / company change
  useEffect(() => {
    if (companies.length > 0) {
      setLoadingSentimentRisk(true);
      getSentimentPortfolioRisk(companies.map(c => c.id), severity)
        .then(setSentimentRisk)
        .catch(() => {})
        .finally(() => setLoadingSentimentRisk(false));
    }
  }, [companies, severity]);

  // ── Select company → fetch detail ────────────────────────────────────────
  const selectCompany = useCallback(async (company: CompanySummary) => {
    setLoadingDetail(true);
    setActivePanel("detail");
    setInsight(null);
    try {
      const detail = await getCompanyRisk(company.id);
      setSelected(detail);
    } catch {
      setSelected(null);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  // ── Fetch companies on mount ──────────────────────────────────────────────
  useEffect(() => {
    getCompanies()
      .then((data) => {
        setCompanies(data);
        if (data.length > 0) {
          selectCompany(data[0]);
        }
      })
      .catch(() => {})
      .finally(() => setLoadingCompanies(false));
  }, [selectCompany]);

  // ── Handle Ticker Search/Ingestion ───────────────────────────────────────
  const handleTickerSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tickerInput.trim()) return;
    setTickerLoading(true);
    const searchVal = tickerInput.trim().toUpperCase();
    try {
      const detail = await getCompanyRisk(searchVal);
      setSelected(detail);
      setTickerInput("");
      
      const refreshed = await getCompanies();
      setCompanies(refreshed);
    } catch (err) {
      alert(`Failed to ingest ticker '${searchVal}'. Ensure it is a valid US public company.`);
    } finally {
      setTickerLoading(false);
    }
  }, [tickerInput]);

  // ── Query bar submit ──────────────────────────────────────────────────────
  const handleQuery = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !query.trim()) return;
    setQueryLoading(true);
    setInsight(null);
    try {
      const data = await getInsight(selected.id, query);
      setInsight(data);
    } catch {
      setInsight(null);
    } finally {
      setQueryLoading(false);
    }
  }, [selected, query]);

  // ── Risk tier counts ─────────────────────────────────────────────────────
  const tierCounts = companies.reduce<Record<string, number>>(
    (acc, c) => { acc[c.risk_tier ?? "Medium"] = (acc[c.risk_tier ?? "Medium"] ?? 0) + 1; return acc; },
    {}
  );

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 px-6 py-3 border-b border-navy-700
                         bg-navy-950">
        <div className="max-w-screen-2xl mx-auto flex items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-electric-500/10 border border-electric-500/30
                           flex items-center justify-center">
              <BarChart3 size={16} className="text-electric-500" />
            </div>
            <div>
              <h1 className="text-sm font-serif font-bold text-[#1C1C1C]">Vantage Risk</h1>
              <p className="text-xs text-stone-600 font-sans">Credit Intelligence Platform</p>
            </div>
          </div>

          {/* Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {(["overview", "portfolio", "news", "benchmark"] as ActivePanel[]).map((panel) => (
              <button
                key={panel}
                onClick={() => setActivePanel(panel)}
                className={`relative px-4 py-1.5 text-xs font-medium capitalize
                  transition-all duration-150
                  ${activePanel === panel
                    ? "text-[#1C1C1C] font-semibold border-b-2 border-electric-500"
                    : "text-stone-500 hover:text-[#1C1C1C]"
                  }`}
              >
                {panel === "news" ? "Predictive Sentiment" : panel}
              </button>
            ))}
          </nav>

          {/* Latency ticker */}
          <LatencyTicker />
        </div>
      </header>

      {/* ── Main Content ────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-6 py-6 gap-6 flex flex-col">

        {/* ── KPI Row ─────────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Companies Tracked",  value: companies.length, icon: Layers,       color: "text-electric-400" },
            { label: "Critical Risk",       value: tierCounts.Critical ?? 0, icon: Zap,  color: "text-violet-400" },
            { label: "High Risk",           value: tierCounts.High ?? 0, icon: AlertTriangle, color: "text-red-400" },
            { label: "Low Risk",            value: tierCounts.Low ?? 0,  icon: Shield,   color: "text-emerald-400" },
          ].map(({ label, value, icon: Icon, color }) => (
            <motion.div
              key={label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="glass-card p-4"
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon size={14} className={color} />
                <span className="text-xs text-slate-500 font-medium">{label}</span>
              </div>
              <p className="text-2xl font-bold text-white font-mono">{value}</p>
            </motion.div>
          ))}
        </div>

        {/* ── Two-column layout ───────────────────────────────────────────── */}
        <div className="flex gap-6 flex-1 min-h-0">

          {/* Left: Company list */}
          <div className="w-64 flex-shrink-0 glass-card p-4 flex flex-col gap-2 overflow-y-auto">
            <p className="section-title">Companies</p>
            
            {/* Ticker Search / Live Ingest */}
            <form onSubmit={handleTickerSearch} className="flex gap-1.5 mb-2">
              <input
                type="text"
                value={tickerInput}
                onChange={(e) => setTickerInput(e.target.value)}
                placeholder="Ingest Ticker (e.g. TSLA)"
                className="input-dark px-2.5 py-1.5 text-xs focus:ring-0 placeholder:text-slate-600 bg-navy-900 border-white/5 text-slate-100 rounded-lg flex-1"
                disabled={tickerLoading}
              />
              <button
                type="submit"
                disabled={tickerLoading || !tickerInput.trim()}
                className="p-1.5 rounded-lg bg-electric-500 hover:bg-electric-400 text-white flex items-center justify-center flex-shrink-0 cursor-pointer disabled:opacity-50"
              >
                {tickerLoading ? (
                  <div className="w-3.5 h-3.5 rounded-full border border-white/30 border-t-white animate-spin" />
                ) : (
                  <Plus size={14} />
                )}
              </button>
            </form>

            {loadingCompanies ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="w-6 h-6 rounded-full border-2 border-cyan-glow/30
                               border-t-cyan-glow animate-spin" />
              </div>
            ) : (
              companies.map((c, i) => (
                <motion.button
                  key={c.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.02 }}
                  onClick={() => selectCompany(c)}
                  className={`
                    w-full text-left px-3 py-2.5 rounded-lg transition-all duration-150
                    flex items-center justify-between gap-2
                    ${selected?.id === c.id
                      ? "bg-electric-500/15 border border-electric-500/30"
                      : "hover:bg-white/5 border border-transparent"
                    }
                  `}
                >
                  <div className="min-w-0">
                    <p className="font-mono text-xs font-semibold text-[#1C1C1C]">{c.ticker}</p>
                    <p className="text-xs text-stone-600 truncate font-medium">{c.name}</p>
                  </div>
                  <div className="flex-shrink-0 flex items-center gap-1">
                    <span className={`
                      text-xs font-mono font-bold
                      ${c.risk_tier === "Low"      ? "text-emerald-400" :
                        c.risk_tier === "Medium"   ? "text-amber-400"   :
                        c.risk_tier === "High"     ? "text-red-400"     :
                        c.risk_tier === "Critical" ? "text-violet-400"  : "text-slate-400"}
                    `}>
                      {Math.round(c.composite_risk_score ?? 50)}
                    </span>
                    <ChevronRight size={12} className="text-slate-600" />
                  </div>
                </motion.button>
              ))
            )}
          </div>

          {/* Right: Main panel */}
          <div className="flex-1 flex flex-col gap-4 min-w-0 overflow-y-auto">

            {/* ── Overview / Heatmap ───────────────────────────────────────── */}
            <AnimatePresence mode="wait">
              {activePanel === "overview" && (
                <motion.div
                  key="overview"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="glass-card p-5"
                >
                  <p className="section-title mb-4">Portfolio Risk Heatmap</p>
                  <PortfolioHeatmap
                    companies={companies}
                    onSelectCompany={(c) => { selectCompany(c); setActivePanel("detail"); }}
                  />
                </motion.div>
              )}

              {/* ── Detail Panel ──────────────────────────────────────────── */}
              {(activePanel === "detail" || activePanel === "overview") && selected && (
                <motion.div
                  key="detail"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="flex flex-col gap-4"
                >
                  {/* Company header */}
                  <div className="glass-card p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="ticker-label">{selected.ticker}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                            badge-${(selected.altman_tier ?? "grey").toLowerCase().replace(" ", "")}`}>
                            {selected.altman_tier ?? "—"}
                          </span>
                        </div>
                        <h2 className="text-xl font-bold text-white">{selected.name}</h2>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {selected.sector} · Period: {selected.period ?? "Latest"}
                          {selected.response_time_ms && (
                            <span className="ml-2 text-cyan-glow/60">
                              ⚡ {selected.response_time_ms.toFixed(1)}ms
                            </span>
                          )}
                        </p>
                      </div>
                      {loadingDetail && (
                        <div className="w-5 h-5 rounded-full border-2 border-cyan-glow/30
                                       border-t-cyan-glow animate-spin flex-shrink-0" />
                      )}
                    </div>
                  </div>

                  {/* Gauge + Radar */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="glass-card p-5 flex flex-col items-center justify-center">
                      <p className="section-title mb-3">Composite Score</p>
                      <CompanyRiskGauge
                        score={selected.composite_risk_score ?? 50}
                        tier={selected.risk_tier}
                        size={140}
                        label={selected.ticker}
                      />
                      <div className="mt-4 space-y-1.5 w-full">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-500">Altman Z</span>
                          <span className="font-mono text-white">{selected.altman_z?.toFixed(2) ?? "—"}</span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-500">Prob. of Default</span>
                          <span className="font-mono text-white">
                            {selected.prob_of_default != null
                              ? `${(selected.prob_of_default * 100).toFixed(2)}%` : "—"}
                          </span>
                        </div>
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-500">Distance-to-Default</span>
                          <span className="font-mono text-white">
                            {selected.distance_to_default?.toFixed(3) ?? "—"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="glass-card p-5">
                      <p className="section-title mb-2">Risk Dimensions</p>
                      <RiskRadarChart company={selected} />
                    </div>
                  </div>

                  {/* SHAP Drivers */}
                  {(selected.top_risk_driver_1 || selected.top_risk_driver_2) && (
                    <div className="glass-card p-5">
                      <p className="section-title mb-3">Risk Drivers (SHAP Attribution)</p>
                      <div className="space-y-2">
                        {[selected.top_risk_driver_1, selected.top_risk_driver_2, selected.top_risk_driver_3]
                          .filter(Boolean)
                          .map((driver, i) => (
                            <motion.div
                              key={i}
                              initial={{ opacity: 0, x: -8 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: i * 0.1 }}
                              className="flex items-start gap-3 p-3 rounded-lg bg-white/3 border border-white/5"
                            >
                              <span className="flex-shrink-0 w-5 h-5 rounded-full
                                             bg-electric-500/20 text-electric-400
                                             flex items-center justify-center text-xs font-bold">
                                {i + 1}
                              </span>
                              <p className="text-xs text-slate-300 leading-relaxed">{driver}</p>
                            </motion.div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Credit Risk Matrix Breakdown */}
                  <div className="glass-card p-5">
                    <p className="section-title mb-3">Credit Risk Matrix Breakdown</p>
                    <RiskMatrixGrid company={selected} />
                  </div>

                  {/* Scenario Simulator */}
                  <div className="glass-card p-5">
                    <p className="section-title mb-3">Rate Shock Scenario</p>
                    <ScenarioSimulator company={selected} />
                  </div>

                  {/* Query bar + Claude insight */}
                  <div className="glass-card p-5">
                    <p className="section-title mb-3">Analyst Query → AI Insight</p>
                    <form onSubmit={handleQuery} className="flex gap-2">
                      <div className="relative flex-1">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2
                                                    text-slate-500 pointer-events-none" />
                        <input
                          type="text"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          placeholder={`Ask about ${selected.ticker}'s credit risk…`}
                          className="input-dark pl-9"
                        />
                      </div>
                      <button
                        type="submit"
                        disabled={queryLoading || !query.trim()}
                        className="btn-primary flex-shrink-0"
                      >
                        {queryLoading ? (
                          <div className="w-4 h-4 rounded-full border-2 border-white/30
                                         border-t-white animate-spin" />
                        ) : (
                          <Zap size={14} />
                        )}
                        Analyze
                      </button>
                    </form>

                    <AnimatePresence>
                      {insight && (
                        <motion.div
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0 }}
                          className="mt-4 p-4 rounded-lg bg-navy-900/80 border border-cyan-glow/10"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs text-slate-500">
                              Claude · {insight.sources_used} filing sources ·{" "}
                              {insight.response_time_ms?.toFixed(0)}ms
                            </span>
                            <span className={`
                              text-xs px-2.5 py-0.5 rounded-full font-medium
                              ${insight.recommendation === "Flag for review" ? "badge-high"  :
                                insight.recommendation === "Low concern"     ? "badge-low"   :
                                "badge-medium"}
                            `}>
                              {insight.recommendation}
                            </span>
                          </div>
                          <p className="text-sm text-slate-200 leading-relaxed typewriter-cursor">
                            {displayedNarrative}
                          </p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              )}

              {/* ── Predictive Sentiment Tab ──────────────────────────────── */}
              {activePanel === "news" && (
                <motion.div
                  key="news"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="space-y-6"
                >
                  {/* Portfolio Predictive VaR Stress Test */}
                  {sentimentRisk && (
                    <div className="glass-card p-5 space-y-4">
                      <div>
                        <h3 className="text-sm font-bold text-white mb-1">Sentiment-Adjusted Portfolio Stress Test</h3>
                        <p className="text-xs text-slate-500 font-mono">
                          Simulating how global news sentiment across portfolio companies shifts default risk.
                        </p>
                      </div>

                      {/* Severity Slider */}
                      <div className="p-4 rounded-xl bg-navy-900 border border-white/5 space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-400 font-medium">Scenario Severity Multiplier</span>
                          <span className="font-mono text-cyan-glow font-bold">{severity.toFixed(1)}x</span>
                        </div>
                        <input
                          type="range"
                          min={0.0}
                          max={2.0}
                          step={0.2}
                          value={severity}
                          onChange={(e) => setSeverity(parseFloat(e.target.value))}
                          className="w-full h-1.5 rounded-full appearance-none bg-white/5 cursor-pointer accent-cyan-glow"
                        />
                        <div className="flex justify-between text-[10px] text-slate-600">
                          <span>0.0x (No Stress)</span>
                          <span>1.0x (Standard)</span>
                          <span>2.0x (Severe Crash)</span>
                        </div>
                      </div>

                      {/* Side-by-side VaR comparison bars */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl bg-navy-950/60 border border-white/5 space-y-2">
                          <p className="text-xs text-slate-500 font-medium font-mono uppercase tracking-wider">Portfolio Value-at-Risk (VaR 95%)</p>
                          <div className="flex justify-between items-end">
                            <div>
                              <p className="text-[10px] text-slate-600 uppercase">Historical</p>
                              <p className="text-lg font-bold text-white font-mono">{sentimentRisk.base_var_95.toFixed(2)}%</p>
                            </div>
                            <div className="text-right">
                              <p className="text-[10px] text-red-400 uppercase font-semibold">Sentiment-Stressed</p>
                              <p className="text-lg font-bold text-red-400 font-mono">{sentimentRisk.sentiment_var_95.toFixed(2)}%</p>
                            </div>
                          </div>
                          <div className="h-2 rounded-full bg-white/5 overflow-hidden flex">
                            <div className="h-full bg-slate-500" style={{ width: `${(sentimentRisk.base_var_95 / 100) * 100}%` }} />
                            <div className="h-full bg-red-500/60" style={{ width: `${((sentimentRisk.sentiment_var_95 - sentimentRisk.base_var_95) / 100) * 100}%` }} />
                          </div>
                        </div>

                        <div className="p-4 rounded-xl bg-navy-950/60 border border-white/5 space-y-2">
                          <p className="text-xs text-slate-500 font-medium font-mono uppercase tracking-wider">Expected Shortfall (CVaR 95%)</p>
                          <div className="flex justify-between items-end">
                            <div>
                              <p className="text-[10px] text-slate-600 uppercase">Historical</p>
                              <p className="text-lg font-bold text-white font-mono">{sentimentRisk.base_cvar_95.toFixed(2)}%</p>
                            </div>
                            <div className="text-right">
                              <p className="text-[10px] text-red-400 uppercase font-semibold">Sentiment-Stressed</p>
                              <p className="text-lg font-bold text-red-400 font-mono">{sentimentRisk.sentiment_cvar_95.toFixed(2)}%</p>
                            </div>
                          </div>
                          <div className="h-2 rounded-full bg-white/5 overflow-hidden flex">
                            <div className="h-full bg-slate-500" style={{ width: `${(sentimentRisk.base_cvar_95 / 100) * 100}%` }} />
                            <div className="h-full bg-red-500/60" style={{ width: `${((sentimentRisk.sentiment_cvar_95 - sentimentRisk.base_cvar_95) / 100) * 100}%` }} />
                          </div>
                        </div>
                      </div>

                      {/* Stressed list */}
                      <div className="space-y-2">
                        <p className="section-title">Portfolio Sentiment Drift</p>
                        <div className="divide-y divide-white/5 max-h-48 overflow-y-auto pr-1">
                          {sentimentRisk.stressed_companies.map((s) => (
                            <div key={s.ticker} className="flex justify-between py-2 text-xs font-mono">
                              <div className="flex items-center gap-2">
                                <span className="text-[#1C1C1C] font-semibold">{s.ticker}</span>
                                <span className={`text-[10px] px-1.5 py-0.5 rounded
                                  ${s.net_sentiment < 0 ? "bg-red-500/10 text-red-400" :
                                    s.net_sentiment > 0 ? "bg-emerald-500/10 text-emerald-400" :
                                    "bg-white/5 text-slate-400"}`}>
                                  Net Sent: {s.net_sentiment > 0 ? "+" : ""}{s.net_sentiment}
                                </span>
                              </div>
                              <div className="flex items-center gap-3">
                                <span className="text-slate-500">Z-Score: {s.base_score}</span>
                                <span className="text-slate-400 font-bold">Stressed: {s.stressed_score}</span>
                                <span className={`w-16 text-center text-[10px] py-0.5 rounded font-semibold
                                  ${s.status === "Stressed" ? "bg-red-500/15 text-red-400" : "bg-white/5 text-slate-500"}`}>
                                  {s.status}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* News feed for selected company */}
                  {selected && (
                    <div className="glass-card p-5 space-y-4">
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="ticker-label">{selected.ticker}</span>
                          <h3 className="text-sm font-bold text-white mt-1">Predictive Sentiment Feed</h3>
                        </div>
                        {loadingNews && (
                          <div className="w-4 h-4 rounded-full border border-cyan-glow/30 border-t-cyan-glow animate-spin" />
                        )}
                      </div>

                      <div className="space-y-3">
                        {news.length === 0 ? (
                          <p className="text-xs text-slate-500">No recent news available for this ticker.</p>
                        ) : (
                          news.map((item, idx) => (
                            <motion.div
                              key={idx}
                              initial={{ opacity: 0, x: -8 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: idx * 0.05 }}
                              className="p-3.5 rounded-xl bg-navy-900/60 border border-white/5 hover:border-white/10 transition-all duration-150 space-y-2 text-left"
                            >
                              <div className="flex items-center justify-between gap-3">
                                <span className="text-[10px] text-slate-500 font-mono">{item.publisher}</span>
                                <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase
                                  ${item.sentiment === "Bullish" ? "badge-low" :
                                    item.sentiment === "Bearish" ? "badge-high" : "badge-medium"}`}>
                                  {item.sentiment} ({item.score > 0 ? "+" : ""}{item.score})
                                </span>
                              </div>

                              <h4 className="text-xs font-bold text-[#E60000] leading-snug">
                                <a href={item.link} target="_blank" rel="noopener noreferrer" className="hover:text-cyan-glow hover:underline">
                                  {item.headline}
                                </a>
                              </h4>

                              {item.summary && (
                                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                                  {item.summary}
                                </p>
                              )}

                              <div className="flex items-center justify-between pt-1">
                                <a
                                  href={item.link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-cyan-glow hover:underline"
                                >
                                  Read Full Article ↗
                                </a>
                              </div>

                              <div className="p-2.5 rounded bg-black/25 text-[11px] text-slate-400 font-mono leading-relaxed border-l-2 border-cyan-glow/40">
                                <span className="text-cyan-glow font-bold mr-1">Credit Forecast:</span>
                                {item.effect}
                              </div>
                            </motion.div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}

              {/* ── Portfolio panel ──────────────────────────────────────── */}
              {activePanel === "portfolio" && (
                <motion.div
                  key="portfolio"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="glass-card p-5"
                >
                  <p className="section-title mb-4">Portfolio Risk Heatmap</p>
                  <PortfolioHeatmap
                    companies={companies}
                    onSelectCompany={(c) => { selectCompany(c); setActivePanel("detail"); }}
                  />
                </motion.div>
              )}

              {/* ── Benchmark panel ──────────────────────────────────────── */}
              {activePanel === "benchmark" && (
                <motion.div
                  key="benchmark"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  className="glass-card p-5 space-y-5"
                >
                  <div>
                    <h3 className="text-sm font-bold text-white mb-1">Latency Benchmark Comparison</h3>
                    <p className="text-xs text-slate-500 font-mono">
                      Comparing naive (un-cached execution) vs optimized (LRU cached) query execution times.
                    </p>
                  </div>

                  {/* Latency Improvement Spotlight */}
                  {latencyStats?.improvement_pct ? (
                    <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-between gap-4">
                      <div>
                        <p className="text-xs text-emerald-400 font-semibold uppercase tracking-wider">Spotlight Result</p>
                        <p className="text-sm text-slate-200 mt-1 leading-relaxed">
                          The optimized cache layer achieved a <b className="text-emerald-400">{latencyStats.improvement_pct}% reduction</b> in p95 query response latency.
                        </p>
                      </div>
                      <div className="flex-shrink-0 text-3xl font-extrabold text-emerald-400 font-mono tracking-tight">
                        -{latencyStats.improvement_pct}%
                      </div>
                    </div>
                  ) : null}

                  {/* Instructions — only show if benchmark has not been run yet */}
                  {!latencyStats?.stats?.some(s => (s.tag === "naive" || s.tag === "optimized") && s.n_requests > 0) ? (
                    <div className="flex items-start gap-2.5 p-3.5 rounded-lg bg-navy-900 border border-white/5 text-xs text-slate-400 leading-relaxed">
                      <AlertTriangle size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
                      <div>
                        To run the automated benchmark harness and log live measurements, run:
                        <code className="block mt-1 p-2 rounded bg-black/40 font-mono text-cyan-glow">
                          python benchmark.py --url http://localhost:8000 --n 100
                        </code>
                      </div>
                    </div>
                  ) : null}

                  {/* Latency Stats Table */}
                  {latencyStats?.stats && latencyStats.stats.length > 0 ? (
                    <div className="space-y-4">
                      <p className="section-title">Execution Times (ms)</p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {latencyStats.stats.map((s) => (
                          <div key={s.tag} className="p-4 rounded-lg bg-navy-900/60 border border-white/5 space-y-3">
                            <div className="flex items-center justify-between">
                              <span className={`text-xs font-bold font-mono tracking-wider uppercase
                                ${s.tag === "optimized" ? "text-emerald-400" : s.tag === "naive" ? "text-red-400" : "text-cyan-glow"}`}>
                                {s.tag}
                              </span>
                              <span className="text-[10px] text-slate-500 font-mono">{s.n_requests} reqs</span>
                            </div>

                            <div className="space-y-2">
                              {[
                                { label: "Average", val: s.avg_ms },
                                { label: "p50 (Median)", val: s.p50_ms },
                                { label: "p95 (Target)", val: s.p95_ms },
                                { label: "p99 (Tail)", val: s.p99_ms },
                              ].map((item) => (
                                <div key={item.label} className="space-y-1">
                                  <div className="flex justify-between text-xs font-mono">
                                    <span className="text-slate-500">{item.label}</span>
                                    <span className="text-white font-medium">{item.val} ms</span>
                                  </div>
                                  <div className="h-1 rounded-full bg-white/5 overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${s.tag === "optimized" ? "bg-emerald-500" : s.tag === "naive" ? "bg-red-500" : "bg-cyan-glow"}`}
                                      style={{ width: `${Math.min(100, (item.val / 2500) * 100)}%` }}
                                    />
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>
    </div>
  );
}
