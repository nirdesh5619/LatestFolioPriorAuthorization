import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AgentStats } from "../api/types";
import { CHART_INK, STATUS } from "./colors";
import { ChartTooltip } from "./ChartTooltip";

interface Props {
  agentStats: AgentStats[];
}

function shortenAgentName(name: string): string {
  return name.replace(/_agent$/, "").replace(/_/g, " ");
}

/**
 * Success vs. error IS a state, so this wears status colors (good/critical),
 * not the categorical theme - the collision rule from the color formula.
 */
export function AgentReliabilityChart({ agentStats }: Props) {
  if (agentStats.length === 0) {
    return <p className="empty-state">No agent runs recorded yet.</p>;
  }

  const data = agentStats.map((a) => ({
    agent: shortenAgentName(a.agent),
    success: a.success_count,
    error: a.error_count,
  }));
  const hasErrors = data.some((d) => d.error > 0);
  const height = Math.max(200, data.length * 46 + 40);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 4 }} barCategoryGap={16}>
        <CartesianGrid horizontal={false} stroke={CHART_INK.gridline} />
        <XAxis
          type="number"
          allowDecimals={false}
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
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(11,11,11,0.04)" }} />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline" />
        <Bar
          dataKey="success"
          name="Success"
          stackId="calls"
          fill={STATUS.good}
          barSize={18}
          radius={hasErrors ? undefined : [0, 4, 4, 0]}
        />
        <Bar dataKey="error" name="Error" stackId="calls" fill={STATUS.critical} barSize={18} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
