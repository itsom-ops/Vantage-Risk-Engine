import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { runScenario } from "../api/api";
import type { CompanySummary, ScenarioResponse } from "../api/api";
import { TrendingDown, TrendingUp, AlertTriangle, Minus } from "lucide-react";

interface ScenarioSimulatorProps {
  company: CompanySummary;
}

const PRESET_SHOCKS = [-200, -100, 0, +100, +200, +300, +500];

export function ScenarioSimulator({ company }: ScenarioSimulatorProps) {
  const [bps, setBps] = useState(0);
  const [result, setResult] = useState<ScenarioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const simulate = useCallback(async (shock: number) => {
    setBps(shock);
    setLoading(true);
    setError(null);
    try {
      const data = await runScenario(company.id, shock);
      setResult(data);
    } catch {
      setError("Scenario simulation failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [company.id]);

  const tierMoved = result?.tier_changed;
  const zDelta = result && result.stressed_altman_z != null && result.base_altman_z != null
    ? result.stressed_altman_z - result.base_altman_z
    : null;

  return (
    <div className="space-y-4">
      {/* Shock selector */}
      <div>
        <p className="section-title">Rate Shock (bps)</p>
        <div className="flex flex-wrap gap-2">
          {PRESET_SHOCKS.map((shock) => (
            <button
              key={shock}
              onClick={() => simulate(shock)}
              className={`
                px-3 py-1.5 rounded-lg text-xs font-mono font-semibold
                border transition-all duration-150
                ${bps === shock
                  ? shock > 0
                    ? "bg-red-500/20 border-red-500/50 text-red-400"
                    : shock < 0
                      ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-400"
                      : "bg-cyan-glow/10 border-cyan-glow/40 text-cyan-glow"
                  : "bg-white/5 border-white/10 text-slate-400 hover:border-white/20"
                }
              `}
            >
              {shock > 0 ? `+${shock}` : shock === 0 ? "Base" : shock}
            </button>
          ))}
        </div>

        {/* Slider */}
        <div className="mt-3">
          <input
            type="range"
            min={-500}
            max={500}
            step={25}
            value={bps}
            onChange={(e) => simulate(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none
                       bg-gradient-to-r from-emerald-500 via-white/10 to-red-500
                       cursor-pointer accent-cyan-glow"
          />
          <div className="flex justify-between text-xs text-slate-600 mt-1">
            <span>-500 bps</span>
            <span>0</span>
            <span>+500 bps</span>
          </div>
        </div>
      </div>

      {/* Loading spinner */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-xs text-slate-400"
          >
            <div className="w-3 h-3 rounded-full border border-cyan-glow/40
                           border-t-cyan-glow animate-spin" />
            Simulating rate shock…
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error */}
      {error && <p className="text-xs text-red-400">{error}</p>}

      {/* Results */}
      <AnimatePresence>
        {result && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.25 }}
            className="space-y-3"
          >
            {/* Z-Score delta */}
            <div className="grid grid-cols-3 gap-2">
              <div className="glass-card p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">Base Z</p>
                <p className="font-mono text-lg font-bold text-white">
                  {result.base_altman_z?.toFixed(2) ?? "—"}
                </p>
                <p className={`text-xs mt-1 badge-${(result.base_tier ?? "grey").toLowerCase().replace(" ", "")}`}>
                  {result.base_tier ?? "—"}
                </p>
              </div>

              <div className="flex flex-col items-center justify-center">
                {zDelta != null && (
                  <div className={`flex items-center gap-1 text-sm font-bold font-mono
                    ${zDelta < 0 ? "text-red-400" : zDelta > 0 ? "text-emerald-400" : "text-slate-400"}`}>
                    {zDelta < -0.01 ? <TrendingDown size={14} /> :
                     zDelta > 0.01  ? <TrendingUp size={14} />  :
                     <Minus size={14} />}
                    {zDelta > 0 ? "+" : ""}{zDelta.toFixed(2)}
                  </div>
                )}
                {tierMoved && (
                  <div className="mt-1">
                    <AlertTriangle size={12} className="text-amber-400 mx-auto" />
                  </div>
                )}
              </div>

              <div className="glass-card p-3 text-center">
                <p className="text-xs text-slate-500 mb-1">Stressed Z</p>
                <p className={`font-mono text-lg font-bold
                  ${zDelta != null && zDelta < 0 ? "text-red-400" : "text-white"}`}>
                  {result.stressed_altman_z?.toFixed(2) ?? "—"}
                </p>
                <p className={`text-xs mt-1 badge-${(result.stressed_tier ?? "grey").toLowerCase().replace(" ", "")}`}>
                  {result.stressed_tier ?? "—"}
                </p>
              </div>
            </div>

            {/* Tier change alert */}
            {tierMoved && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-start gap-2 p-3 rounded-lg
                           bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300"
              >
                <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                <span>
                  Risk tier migrated: <b>{result.base_tier}</b> → <b>{result.stressed_tier}</b>
                </span>
              </motion.div>
            )}

            {/* Narrative */}
            <p className="text-xs text-slate-400 leading-relaxed">{result.narrative}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
