import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { getCompanyRiskMatrix } from "../api/api";
import type { CompanyRiskDetail, RiskMatrixResponse, RiskLeaf } from "../api/api";
import { Shield, AlertOctagon, Scale, Globe, Users, TrendingUp, AlertTriangle } from "lucide-react";

interface RiskMatrixGridProps {
  company: CompanyRiskDetail;
}

interface MatrixCategory {
  title: string;
  icon: React.FC<any>;
  leaves: RiskLeaf[];
  description: string;
}

export function RiskMatrixGrid({ company }: RiskMatrixGridProps) {
  const [matrix, setMatrix] = useState<RiskMatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCompanyRiskMatrix(company.id)
      .then((data) => {
        setMatrix(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load risk matrix:", err);
        setLoading(false);
      });
  }, [company.id]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="p-4 rounded-xl border bg-navy-900/60 border-white/5 animate-pulse h-48 flex flex-col justify-between">
            <div className="h-4 bg-white/5 rounded w-1/3 mb-4"></div>
            <div className="space-y-2">
              <div className="h-3 bg-white/5 rounded w-full"></div>
              <div className="h-3 bg-white/5 rounded w-5/6"></div>
              <div className="h-3 bg-white/5 rounded w-4/6"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!matrix) {
    return (
      <div className="p-8 text-center text-slate-500 font-mono text-sm border border-dashed border-white/5 rounded-xl">
        No computed risk matrix available for {company.ticker}.
      </div>
    );
  }

  // Map backend categories to our UI representation
  const categories: MatrixCategory[] = [
    {
      title: "Credit Risks",
      icon: Shield,
      leaves: matrix.credit_risks || [],
      description: "Default exposure, asset structures, and covenant deltas.",
    },
    {
      title: "Liquidity Risks",
      icon: AlertTriangle,
      leaves: matrix.liquidity_risks || [],
      description: "Working capital buffers and short-term liability coverage.",
    },
    {
      title: "Governance Risks",
      icon: Users,
      leaves: matrix.governance_risks || [],
      description: "Ownership concentration and retained reserves.",
    },
    {
      title: "Market Risks",
      icon: TrendingUp,
      leaves: matrix.market_risks || [],
      description: "EBIT margins relative to asset yields and volatility.",
    },
    {
      title: "External Risks",
      icon: Globe,
      leaves: matrix.external_risks || [],
      description: "Macro interest rate correlations and competitor Altman Z comparison.",
    },
    {
      title: "Legal & Compliance",
      icon: Scale,
      leaves: matrix.legal_compliance || [],
      description: "SEC filing transparency and regulatory keywords.",
    },
  ];

  // Helper to compute overall category severity based on leaf severities
  const getCategorySeverity = (leaves: RiskLeaf[]): "Low" | "Medium" | "High" => {
    if (leaves.some((l) => l.severity === "High")) return "High";
    if (leaves.some((l) => l.severity === "Medium")) return "Medium";
    return "Low";
  };

  const levelBadges: Record<string, string> = {
    Low: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    Medium: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    High: "bg-rose-500/10 text-rose-400 border border-rose-500/20",
  };

  const leafBadges: Record<string, string> = {
    Low: "text-emerald-400 bg-emerald-500/10",
    Medium: "text-amber-400 bg-amber-500/10",
    High: "text-rose-400 bg-rose-500/10",
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {categories.map((cat, idx) => {
        const Icon = cat.icon;
        const categorySeverity = getCategorySeverity(cat.leaves);
        
        return (
          <motion.div
            key={cat.title}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="p-5 rounded-xl border bg-navy-900/60 border-white/5 flex flex-col justify-between hover:border-cyan-glow/20 transition-all duration-200"
          >
            <div>
              {/* Header */}
              <div className="flex items-center justify-between gap-3 mb-2">
                <div className="flex items-center gap-2">
                  <Icon size={15} className="text-cyan-glow" />
                  <span className="font-mono text-sm font-bold text-white">{cat.title}</span>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-md font-mono font-bold uppercase ${levelBadges[categorySeverity]}`}>
                  {categorySeverity}
                </span>
              </div>

              <p className="text-[11px] text-slate-500 leading-normal mb-4">{cat.description}</p>

              {/* Computed Leaves */}
              <div className="space-y-3.5">
                {cat.leaves.map((leaf, i) => (
                  <div key={i} className="pl-3 border-l border-white/10 flex flex-col gap-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-medium text-slate-300 leading-tight">
                        {leaf.title}
                      </span>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-[11px] font-mono font-bold text-cyan-glow">
                          {leaf.value}
                        </span>
                        <span className={`text-[8px] px-1 py-0.5 rounded font-mono uppercase ${leafBadges[leaf.severity]}`}>
                          {leaf.severity}
                        </span>
                      </div>
                    </div>
                    {leaf.explanation && (
                      <p className="text-[10px] text-slate-500 leading-normal italic">
                        {leaf.explanation}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
