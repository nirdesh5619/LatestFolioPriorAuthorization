import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AgentStats } from "../api/types";
import { CATEGORICAL, CHART_INK } from "./colors";
import { ChartTooltip } from "./ChartTooltip";

interface Props {
  agentStats: AgentStats[];
}

function shortenAgentName(name: string): string {
  return name.replace(/_agent$/, "").replace(/_/g, " ");
}

function formatMs(v: number): string {
  return v >= 1 ? `${v.toFixed(0)} ms` : `${v.toFixed(2)} ms`;
}

/**
 * Compares two measures (avg, p95) per agent - a "tell distinct series apart"
 * job, so this uses the fixed-order categorical slots (not status colors:
 * neither measure is a state). Log scale because retrieval's embedding call
 * can be 1,000x slower than the other agents on a cold start.
 */
export function AgentLatencyChart({ agentStats }: Props) {
  if (agentStats.length === 0) {
    return <p className="empty-state">No agent runs recorded yet.</p>;
  }

  const data = agentStats.map((a) => ({
    agent: shortenAgentName(a.agent),
    avg: Math.max(a.avg_execution_time_ms, 0.001),
    p95: Math.max(a.p95_execution_time_ms, 0.001),
  }));

  const height = Math.max(200, data.length * 46 + 40);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 4 }} barCategoryGap={16}>
        <CartesianGrid horizontal={false} stroke={CHART_INK.gridline} />
        <XAxis
          type="number"
          scale="log"
          domain={["auto", "auto"]}
          tickFormatter={formatMs}
          stroke={CHART_INK.muted}
          tick={{ fontSize: 12, fill: CHART_INK.muted }}
          axisLine={{ stroke: CHART_INK.gridline }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="agent"
          width={150}
          stroke={CHART_INK.muted}
          tick={{ fontSize: 12, fill: CHART_INK.secondary }}
          axisLine={{ stroke: CHART_INK.gridline }}
          tickLine={false}
        />
        <Tooltip
          content={<ChartTooltip valueFormatter={(v) => formatMs(Number(v))} />}
          cursor={{ fill: "rgba(11,11,11,0.04)" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline" />
        <Bar dataKey="avg" name="Avg" fill={CATEGORICAL.slot1} barSize={18} radius={[0, 4, 4, 0]} />
        <Bar dataKey="p95" name="P95" fill={CATEGORICAL.slot2} barSize={18} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
