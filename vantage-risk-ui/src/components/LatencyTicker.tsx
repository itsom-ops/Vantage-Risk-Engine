import { useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
// @ts-ignore
import { Sparklines, SparklinesLine } from "react-sparklines";
import { getLatencyStats } from "../api/api";
import type { LatencyStatsResponse } from "../api/api";
import { Activity, Zap } from "lucide-react";

// Fallback sparkline if react-sparklines isn't available — simple SVG
function SimpleSpark({ data }: { data: number[] }) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 64, h = 24;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`)
    .join(" ");
  return (
    <svg width={w} height={h} className="opacity-60">
      <polyline points={pts} fill="none" stroke="#E60000" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

export function LatencyTicker() {
  const [stats, setStats] = useState<LatencyStatsResponse | null>(null);
  const [recentMs, setRecentMs] = useState<number[]>([]);
  const [lastMs, setLastMs] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  const fetchStats = async () => {
    const t0 = performance.now();
    try {
      const data = await getLatencyStats();
      const elapsed = performance.now() - t0;
      setStats(data);
      setLastMs(Math.round(elapsed));
      setRecentMs((prev) => [...prev.slice(-29), Math.round(elapsed)]);
    } catch {
      // silent fail — ticker is non-critical
    }
  };

  useEffect(() => {
    fetchStats();
    pollRef.current = setInterval(fetchStats, 5000);
    return () => clearInterval(pollRef.current);
  }, []);

  const liveStats = stats?.stats.find((s) => s.tag === "live");
  const optimizedStats = stats?.stats.find((s) => s.tag === "optimized");
  const improvementPct = stats?.improvement_pct;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-4 px-4 py-2 rounded-xl
                 glass-card border-navy-700 text-xs"
    >
      {/* Live dot */}
      <div className="flex items-center gap-1.5">
        <span className="live-dot" />
        <span className="text-stone-600 font-medium">LIVE</span>
      </div>

      {/* Last response time */}
      <div className="flex items-center gap-1.5">
        <Activity size={11} className="text-electric-500" />
        <span className="text-stone-600">Last:</span>
        <motion.span
          key={lastMs}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-mono font-semibold text-[#1C1C1C]"
        >
          {lastMs != null ? `${lastMs}ms` : "—"}
        </motion.span>
      </div>

      {/* Sparkline */}
      <div className="hidden sm:block">
        <SimpleSpark data={recentMs} />
      </div>

      {/* p95 from DB */}
      {liveStats && (
        <div className="hidden md:flex items-center gap-1.5">
          <span className="text-stone-600">p95:</span>
          <span className="font-mono font-semibold text-electric-500">
            {liveStats.p95_ms}ms
          </span>
        </div>
      )}

      {/* Improvement badge */}
      {improvementPct != null && improvementPct > 0 && (
        <div className="hidden lg:flex items-center gap-1 px-2 py-0.5 rounded-full
                        bg-green-100/60 border border-risk-low/30 text-risk-low">
          <Zap size={10} />
          <span className="font-semibold">{improvementPct}% faster</span>
        </div>
      )}
    </motion.div>
  );
}
