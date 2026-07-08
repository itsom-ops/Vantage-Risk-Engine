import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { CompanySummary, InsightResponse } from "../api/api";
import { getInsight } from "../api/api";
import { AlertTriangle, TrendingUp, Shield, Zap } from "lucide-react";

interface PortfolioHeatmapProps {
  companies: CompanySummary[];
  onSelectCompany: (company: CompanySummary) => void;
}

const TIER_BG: Record<string, string> = {
  Low:      "bg-green-100/60 border-risk-low/30 hover:bg-green-100",
  Medium:   "bg-amber-100/60 border-risk-medium/30 hover:bg-amber-100",
  High:     "bg-red-100/60   border-electric-500/30 hover:bg-red-100",
  Critical: "bg-red-100      border-risk-critical/30 hover:bg-red-200",
};

const TIER_TEXT: Record<string, string> = {
  Low:      "text-risk-low",
  Medium:   "text-risk-medium",
  High:     "text-electric-500",
  Critical: "text-risk-critical",
};

const TIER_ICON: Record<string, React.FC<any>> = {
  Low:      Shield,
  Medium:   TrendingUp,
  High:     AlertTriangle,
  Critical: Zap,
};

interface TooltipState {
  company: CompanySummary;
  insight: InsightResponse | null;
  loading: boolean;
}

export function PortfolioHeatmap({ companies, onSelectCompany }: PortfolioHeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const handleHover = async (company: CompanySummary) => {
    setTooltip({ company, insight: null, loading: true });
    try {
      const insight = await getInsight(
        company.id,
        `What is the primary credit risk for ${company.name}?`
      );
      setTooltip((prev) =>
        prev?.company.id === company.id
          ? { company, insight, loading: false }
          : prev
      );
    } catch {
      setTooltip((prev) =>
        prev?.company.id === company.id
          ? { company, insight: null, loading: false }
          : prev
      );
    }
  };

  return (
    <div className="relative">
      {/* Grid */}
      <div className="grid grid-cols-5 gap-2 sm:grid-cols-6 lg:grid-cols-8">
        {companies.map((company, i) => {
          const tier = company.risk_tier ?? "Medium";
          const Icon = TIER_ICON[tier] ?? TrendingUp;
          const score = company.composite_risk_score ?? 50;

          return (
            <motion.button
              key={company.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.03, duration: 0.3 }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => onSelectCompany(company)}
              onMouseEnter={() => handleHover(company)}
              onMouseLeave={() => setTooltip(null)}
              className={`
                relative p-2.5 rounded-lg border text-left cursor-pointer
                transition-all duration-200 ${TIER_BG[tier]}
              `}
            >
              <p className="font-mono text-xs font-semibold text-[#1C1C1C] mb-1">
                {company.ticker}
              </p>
              <div className="flex items-center gap-1">
                <Icon size={10} className={TIER_TEXT[tier]} />
                <span className={`text-xs font-bold ${TIER_TEXT[tier]}`}>
                  {Math.round(score)}
                </span>
              </div>
              {/* Risk level bar */}
              <div className="mt-1.5 h-0.5 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    background: TIER_TEXT[tier].replace("text-", "rgb("),
                    backgroundColor:
                      tier === "Low"      ? "#10b981" :
                      tier === "Medium"   ? "#f59e0b" :
                      tier === "High"     ? "#ef4444" : "#7c3aed",
                  }}
                  initial={{ width: 0 }}
                  animate={{ width: `${score}%` }}
                  transition={{ delay: i * 0.03 + 0.3, duration: 0.8, ease: "easeOut" }}
                />
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Floating insight tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.15 }}
            className="mt-3 mx-auto w-full max-w-xl z-[999]
                       glass-card p-4 shadow-card pointer-events-none"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className="font-mono font-bold text-xs text-[#1C1C1C]">{tooltip.company.ticker}</span>
              <span className="text-xs text-stone-600">{tooltip.company.name}</span>
            </div>

            {tooltip.loading ? (
              <div className="flex items-center gap-2 text-xs text-stone-600">
                <div className="w-3 h-3 rounded-full border border-electric-500/40
                               border-t-electric-500 animate-spin" />
                Generating insight…
              </div>
            ) : tooltip.insight ? (
              <>
                <p className="text-xs text-[#1C1C1C] leading-relaxed mb-2">
                  {tooltip.insight.narrative}
                </p>
                <div className={`
                  inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium
                  ${tooltip.insight.recommendation === "Flag for review"
                    ? "badge-high"
                    : tooltip.insight.recommendation === "Low concern"
                      ? "badge-low"
                      : "badge-medium"}
                `}>
                  {tooltip.insight.recommendation}
                </div>
              </>
            ) : (
              <p className="text-xs text-stone-500">Hover to load risk insight</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
