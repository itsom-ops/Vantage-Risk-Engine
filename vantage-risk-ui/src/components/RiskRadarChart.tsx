import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { motion } from "framer-motion";
import type { CompanyRiskDetail } from "../api/api";

interface RiskRadarChartProps {
  company: CompanyRiskDetail;
}

function clamp01(v: number | null | undefined): number {
  if (v == null) return 0.5;
  return Math.max(0, Math.min(1, v));
}

// Normalise each Altman factor to 0-100 for the radar (higher = riskier)
function toRadar(company: CompanyRiskDetail) {
  // Leverage (X4 inverted — lower ratio = higher risk)
  const x4 = company.x4_equity_debt_ratio ?? 1.0;
  const leverageRisk = clamp01(1 - x4 / 3.0) * 100;

  // Liquidity (X1 inverted — negative WC = max risk)
  const x1 = company.x1_working_cap_ratio ?? 0.1;
  const liquidityRisk = clamp01(1 - (x1 + 0.2) / 0.5) * 100;

  // Profitability (X3 inverted)
  const x3 = company.x3_ebit_ratio ?? 0.05;
  const profitRisk = clamp01(1 - (x3 + 0.1) / 0.3) * 100;

  // Volatility (direct)
  const pd = company.prob_of_default ?? 0.02;
  const volatilityRisk = clamp01(pd / 0.15) * 100;

  // Sentiment (composite score proxy)
  const score = company.composite_risk_score ?? 50;
  const sentimentRisk = score;

  return [
    { axis: "Leverage",      value: Math.round(leverageRisk) },
    { axis: "Liquidity",     value: Math.round(liquidityRisk) },
    { axis: "Profitability", value: Math.round(profitRisk) },
    { axis: "Volatility",    value: Math.round(volatilityRisk) },
    { axis: "Sentiment",     value: Math.round(sentimentRisk) },
  ];
}

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card px-3 py-2 text-xs">
      <p className="text-[#1C1C1C] font-semibold">{payload[0]?.payload?.axis}</p>
      <p className="text-electric-500 font-mono font-medium">{payload[0]?.value}</p>
    </div>
  );
};

export function RiskRadarChart({ company }: RiskRadarChartProps) {
  const data = toRadar(company);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.92 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="w-full h-52"
    >
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 20 }}>
          <PolarGrid
            gridType="polygon"
            stroke="#DDD9CE"
            strokeDasharray="3 3"
          />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: "#1C1C1C", fontSize: 11, fontFamily: "Inter" }}
          />
          <Radar
            name={company.ticker}
            dataKey="value"
            stroke="#E60000"
            fill="#E60000"
            fillOpacity={0.12}
            strokeWidth={1.5}
            dot={{ fill: "#E60000", r: 3 }}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
