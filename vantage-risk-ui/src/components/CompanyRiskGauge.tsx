import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useRef } from "react";

interface CompanyRiskGaugeProps {
  score: number;         // 0-100, higher = riskier
  tier: string | null;
  size?: number;
  label?: string;
  animated?: boolean;
}

const TIER_COLORS: Record<string, string> = {
  Low:      "#15803d",
  Medium:   "#b45309",
  High:     "#E60000",
  Critical: "#991b1b",
};

const TIER_GLOW: Record<string, string> = {
  Low:      "rgba(21, 128, 61, 0.2)",
  Medium:   "rgba(180, 83, 9, 0.2)",
  High:     "rgba(230, 0, 0, 0.25)",
  Critical: "rgba(153, 27, 27, 0.25)",
};

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx: number, cy: number, r: number, start: number, end: number) {
  const s = polarToCartesian(cx, cy, r, start);
  const e = polarToCartesian(cx, cy, r, end);
  const large = end - start > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}

export function CompanyRiskGauge({
  score,
  tier,
  size = 160,
  label,
  animated = true,
}: CompanyRiskGaugeProps) {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size * 0.38;
  const strokeWidth = size * 0.065;

  // Score → angle: 0 = -135°, 100 = +135° (270° sweep)
  const scoreSpring = useSpring(0, { stiffness: 40, damping: 15 });
  const angleDeg = useTransform(scoreSpring, [0, 100], [-135, 135]);

  useEffect(() => {
    scoreSpring.set(score);
  }, [score, scoreSpring]);

  const color      = TIER_COLORS[tier ?? "Medium"] ?? "#f59e0b";
  const glowColor  = TIER_GLOW[tier ?? "Medium"] ?? "rgba(245, 158, 11, 0.3)";

  // Background track arc (-135° → 135°)
  const trackPath = describeArc(cx, cy, radius, -135, 135);

  return (
    <div className="flex flex-col items-center gap-2">
      <motion.svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {/* Glow filter */}
        <defs>
          <filter id={`glow-${score}`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Background track */}
        <path
          d={trackPath}
          fill="none"
          stroke="rgba(28,28,28,0.12)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Colored arc — animated */}
        <motion.path
          d={trackPath}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${2 * Math.PI * radius * (270 / 360)} 9999`}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: score / 100 }}
          transition={{ duration: 1.2, ease: "easeOut", delay: 0.1 }}
          style={{ filter: `drop-shadow(0 0 6px ${glowColor})` }}
        />

        {/* Needle dot */}
        <motion.circle
          cx={cx}
          cy={cy - radius}
          r={strokeWidth * 0.7}
          fill={color}
          style={{
            originX: `${cx}px`,
            originY: `${cy}px`,
            rotate: angleDeg,
            filter: `drop-shadow(0 0 4px ${glowColor})`,
          }}
        />

        {/* Score text */}
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#1C1C1C"
          fontSize={size * 0.22}
          fontWeight="700"
          fontFamily="Inter, sans-serif"
        >
          {Math.round(score)}
        </text>
        <text
          x={cx}
          y={cy + size * 0.18}
          textAnchor="middle"
          fill="#78716c"
          fontSize={size * 0.085}
          fontFamily="Inter, sans-serif"
        >
          RISK SCORE
        </text>
      </motion.svg>

      {tier && (
        <motion.span
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className={`
            px-3 py-1 rounded-full text-xs font-semibold tracking-wide
            badge-${tier.toLowerCase().replace(" ", "")}
          `}
        >
          {tier}
        </motion.span>
      )}
      {label && (
        <p className="text-xs text-slate-500 font-mono tracking-widest uppercase">{label}</p>
      )}
    </div>
  );
}
