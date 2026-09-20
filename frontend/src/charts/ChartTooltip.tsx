interface TooltipPayloadEntry {
  dataKey?: string | number;
  name?: string | number;
  value?: number | string;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string | number;
  valueFormatter?: (value: number | string | undefined) => string;
}

function defaultFormatValue(value: number | string | undefined): string {
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return value ?? "";
}

/** Values lead, series name follows; each row keyed by a short line, not a box. */
export function ChartTooltip({ active, payload, label, valueFormatter }: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const format = valueFormatter ?? defaultFormatValue;

  return (
    <div className="chart-tooltip">
      {label !== undefined && <div className="chart-tooltip-title">{label}</div>}
      {payload.map((entry, idx) => (
        <div className="chart-tooltip-row" key={`${entry.dataKey ?? entry.name ?? idx}`}>
          <span className="chart-tooltip-key" style={{ background: entry.color }} />
          <span className="chart-tooltip-label">{entry.name}</span>
          <strong className="chart-tooltip-value">{format(entry.value)}</strong>
        </div>
      ))}
    </div>
  );
}
