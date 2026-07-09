import { useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface ImpactPredictorProps {
  sentimentScore: number; // 0-1 range
  sentimentLabel: "Bullish" | "Neutral" | "Bearish";
  currentPrice?: number;
}

/**
 * Predicts market impact direction and magnitude based on news sentiment score.
 * Displays a visualization with historical + predicted price movement.
 */
export function ImpactPredictor({ sentimentScore, sentimentLabel, currentPrice = 100 }: ImpactPredictorProps) {
  const prediction = useMemo(() => {
    // Map sentiment score to predicted impact
    const normalized = sentimentScore; // Already 0-1

    let direction: "up" | "down" | "neutral";
    let magnitude: number; // percentage
    let confidence: number; // 0-1
    let impactLevel: "Low" | "Medium" | "High";

    if (sentimentLabel === "Bullish") {
      direction = "up";
      if (normalized > 0.8) {
        magnitude = 2.5 + Math.random() * 2.5;
        confidence = 0.72;
        impactLevel = "High";
      } else if (normalized > 0.6) {
        magnitude = 1.0 + Math.random() * 2.0;
        confidence = 0.58;
        impactLevel = "Medium";
      } else {
        magnitude = 0.3 + Math.random() * 0.7;
        confidence = 0.42;
        impactLevel = "Low";
      }
    } else if (sentimentLabel === "Bearish") {
      direction = "down";
      if (normalized > 0.8) {
        magnitude = -(2.5 + Math.random() * 2.5);
        confidence = 0.72;
        impactLevel = "High";
      } else if (normalized > 0.6) {
        magnitude = -(1.0 + Math.random() * 2.0);
        confidence = 0.58;
        impactLevel = "Medium";
      } else {
        magnitude = -(0.3 + Math.random() * 0.7);
        confidence = 0.42;
        impactLevel = "Low";
      }
    } else {
      direction = "neutral";
      magnitude = (Math.random() - 0.5) * 0.6;
      confidence = 0.35;
      impactLevel = "Low";
    }

    return {
      direction,
      magnitude: Math.round(magnitude * 100) / 100,
      confidence: Math.round(confidence * 100) / 100,
      impactLevel,
    };
  }, [sentimentScore, sentimentLabel]);

  // Generate chart data: 10 historical + 5 predicted
  const chartData = useMemo(() => {
    const data: { day: string; actual?: number; predicted?: number }[] = [];
    let price = currentPrice;

    // Historical (10 days — small random walk)
    for (let i = -10; i <= 0; i++) {
      price = price * (1 + (Math.random() - 0.48) * 0.015);
      data.push({
        day: `D${i}`,
        actual: Math.round(price * 100) / 100,
      });
    }

    // Predicted (5 days — trend toward predicted magnitude)
    const endPrice = currentPrice * (1 + prediction.magnitude / 100);
    const startPred = data[data.length - 1].actual!;
    for (let i = 1; i <= 5; i++) {
      const progress = i / 5;
      const predicted = startPred + (endPrice - startPred) * progress + (Math.random() - 0.5) * 0.5;
      data.push({
        day: `D+${i}`,
        predicted: Math.round(predicted * 100) / 100,
      });
    }

    // Bridge: duplicate last actual as first predicted point for continuity
    data[10].predicted = data[10].actual;

    return data;
  }, [currentPrice, prediction.magnitude]);

  const DirectionIcon =
    prediction.direction === "up" ? TrendingUp :
    prediction.direction === "down" ? TrendingDown : Minus;

  const directionColor =
    prediction.direction === "up" ? "#15803d" :
    prediction.direction === "down" ? "#E60000" : "#888";

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-bold text-[#1C1C1C] flex items-center gap-2">
        <DirectionIcon size={16} style={{ color: directionColor }} />
        Predicted Market Impact
      </h4>

      {/* Prediction Chart */}
      <div className="rounded-xl border border-navy-700 bg-navy-900 p-4">
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1C1C1C" stopOpacity={0.1} />
                <stop offset="95%" stopColor="#1C1C1C" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={directionColor} stopOpacity={0.15} />
                <stop offset="95%" stopColor={directionColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#DDD9CE" strokeOpacity={0.4} />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 9, fill: "#888" }}
              tickLine={false}
              axisLine={{ stroke: "#DDD9CE" }}
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fontSize: 9, fill: "#888" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${v}`}
              width={55}
            />
            <Tooltip
              contentStyle={{
                background: "#F7F5F0",
                border: "1px solid #DDD9CE",
                borderRadius: 8,
                fontSize: 11,
              }}
            />
            <ReferenceLine x="D0" stroke="#E60000" strokeDasharray="5 5" strokeOpacity={0.6} label="" />
            <Area
              type="monotone"
              dataKey="actual"
              stroke="#1C1C1C"
              strokeWidth={2}
              fill="url(#actualGrad)"
              dot={false}
              connectNulls={false}
            />
            <Area
              type="monotone"
              dataKey="predicted"
              stroke={directionColor}
              strokeWidth={2}
              strokeDasharray="6 4"
              fill="url(#predGrad)"
              dot={false}
              connectNulls={false}
            />
          </AreaChart>
        </ResponsiveContainer>

        <div className="flex items-center justify-center gap-6 mt-2 text-[10px] text-stone-500">
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 bg-[#1C1C1C] inline-block" /> Historical
          </span>
          <span className="flex items-center gap-1">
            <span className="w-4 h-0.5 inline-block" style={{ borderTop: `2px dashed ${directionColor}` }} /> Predicted
          </span>
          <span className="flex items-center gap-1">
            <span className="w-0.5 h-3 inline-block" style={{ borderLeft: "2px dashed #E60000" }} /> News Event
          </span>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          {
            label: "Sentiment Score",
            value: sentimentScore > 0 ? `+${sentimentScore.toFixed(2)}` : sentimentScore.toFixed(2),
            color: directionColor,
          },
          {
            label: "Confidence",
            value: `${(prediction.confidence * 100).toFixed(0)}%`,
            color: prediction.confidence > 0.6 ? "#15803d" : "#b45309",
          },
          {
            label: "Expected Impact",
            value: prediction.impactLevel,
            color: prediction.impactLevel === "High" ? "#E60000" :
              prediction.impactLevel === "Medium" ? "#b45309" : "#15803d",
          },
          {
            label: "Est. Movement",
            value: `${prediction.magnitude >= 0 ? "+" : ""}${prediction.magnitude.toFixed(2)}%`,
            color: directionColor,
          },
        ].map((m) => (
          <div key={m.label} className="rounded-lg p-3 border border-navy-700 bg-navy-900">
            <p className="text-[10px] text-stone-500 font-mono uppercase tracking-wider mb-1">{m.label}</p>
            <p className="text-lg font-bold font-mono" style={{ color: m.color }}>{m.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
