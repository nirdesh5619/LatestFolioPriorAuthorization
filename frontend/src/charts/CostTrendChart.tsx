import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CostTimeseriesPoint } from "../api/types";
import { CATEGORICAL, CHART_INK } from "./colors";
import { ChartTooltip } from "./ChartTooltip";

interface Props {
  timeseries: CostTimeseriesPoint[];
}

function formatUsd(v: number): string {
  return `$${v.toFixed(v < 1 ? 4 : 2)}`;
}

/** A single cost-over-time series - a line, not a bar, since the reader's task is trend
 * direction across a filtered date range rather than comparing discrete categories. */
export function CostTrendChart({ timeseries }: Props) {
  if (timeseries.length === 0) {
    return <p className="empty-state">No LLM spend in this range.</p>;
  }

  const data = timeseries.map((p) => ({ date: p.date, cost: p.cost_usd }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 20, bottom: 4, left: 4 }}>
        <CartesianGrid vertical={false} stroke={CHART_INK.gridline} />
        <XAxis
          dataKey="date"
          stroke={CHART_INK.muted}
          tick={{ fontSize: 11, fill: CHART_INK.muted }}
          axisLine={{ stroke: CHART_INK.gridline }}
          tickLine={false}
          minTickGap={24}
        />
        <YAxis
          tickFormatter={formatUsd}
          stroke={CHART_INK.muted}
          tick={{ fontSize: 11, fill: CHART_INK.muted }}
          axisLine={{ stroke: CHART_INK.gridline }}
          tickLine={false}
          width={64}
        />
        <Tooltip content={<ChartTooltip valueFormatter={(v) => formatUsd(Number(v))} />} cursor={{ stroke: CHART_INK.gridline }} />
        <Line
          type="monotone"
          dataKey="cost"
          name="Cost"
          stroke={CATEGORICAL.slot1}
          strokeWidth={2}
          dot={data.length <= 31}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
