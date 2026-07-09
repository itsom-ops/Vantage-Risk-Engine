import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Bar,
  BarChart,
} from "recharts";
import type { PricePoint } from "../api/api";

interface PriceChartProps {
  points: PricePoint[];
  range: string;
  height?: number;
  showVolume?: boolean;
}

function formatTimestamp(ts: string, range: string): string {
  const d = new Date(ts);
  if (range === "1d" || range === "1w") {
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  }
  if (range === "1m" || range === "3m") {
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function formatPrice(val: number): string {
  return val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatVolume(vol: number): string {
  if (vol >= 1_000_000_000) return `${(vol / 1_000_000_000).toFixed(1)}B`;
  if (vol >= 1_000_000) return `${(vol / 1_000_000).toFixed(1)}M`;
  if (vol >= 1_000) return `${(vol / 1_000).toFixed(1)}K`;
  return String(vol);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;

  return (
    <div className="rounded-lg p-3 shadow-lg border"
         style={{
           background: "#F7F5F0",
           borderColor: "#DDD9CE",
           minWidth: 180,
         }}>
      <p className="text-[10px] font-mono text-stone-500 mb-1">{label}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
        <span className="text-stone-500">Open</span>
        <span className="font-mono font-semibold text-[#1C1C1C]">${formatPrice(d.open)}</span>
        <span className="text-stone-500">High</span>
        <span className="font-mono font-semibold text-emerald-600">${formatPrice(d.high)}</span>
        <span className="text-stone-500">Low</span>
        <span className="font-mono font-semibold text-red-600">${formatPrice(d.low)}</span>
        <span className="text-stone-500">Close</span>
        <span className="font-mono font-semibold text-[#1C1C1C]">${formatPrice(d.close)}</span>
        <span className="text-stone-500">Volume</span>
        <span className="font-mono font-semibold text-[#1C1C1C]">{formatVolume(d.volume)}</span>
      </div>
    </div>
  );
};

export function PriceChart({ points, range, height = 360, showVolume = true }: PriceChartProps) {
  const chartData = useMemo(() => {
    return points.map((p) => ({
      ...p,
      label: formatTimestamp(p.timestamp, range),
    }));
  }, [points, range]);

  const isPositive = useMemo(() => {
    if (chartData.length < 2) return true;
    return chartData[chartData.length - 1].close >= chartData[0].open;
  }, [chartData]);

  const lineColor = isPositive ? "#15803d" : "#E60000";
  const gradientId = isPositive ? "priceGradientUp" : "priceGradientDown";

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center text-stone-500 text-sm" style={{ height }}>
        No price data available
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Price Area Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={lineColor} stopOpacity={0.2} />
              <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#DDD9CE" strokeOpacity={0.5} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "#888" }}
            tickLine={false}
            axisLine={{ stroke: "#DDD9CE" }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 10, fill: "#888" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `$${v}`}
            width={65}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="close"
            stroke={lineColor}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, stroke: lineColor, strokeWidth: 2, fill: "#F7F5F0" }}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Volume Bar Chart */}
      {showVolume && (
        <ResponsiveContainer width="100%" height={80}>
          <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="label" tick={false} axisLine={false} tickLine={false} />
            <YAxis
              tick={{ fontSize: 9, fill: "#aaa" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatVolume}
              width={65}
            />
            <Bar
              dataKey="volume"
              fill={lineColor}
              opacity={0.3}
              radius={[2, 2, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
