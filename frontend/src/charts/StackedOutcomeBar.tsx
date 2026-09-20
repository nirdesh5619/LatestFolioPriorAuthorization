import { useState } from "react";

export interface OutcomeSegment {
  key: string;
  label: string;
  value: number;
  color: string;
}

interface Props {
  segments: OutcomeSegment[];
  emptyMessage?: string;
}

/**
 * A single horizontal stacked bar for a small part-to-whole status breakdown
 * (2-3 categories). Per the dataviz skill, a pie/donut is the wrong form here -
 * a stacked bar reads magnitude and share at once and stays legible at a glance.
 */
export function StackedOutcomeBar({ segments, emptyMessage = "No data yet." }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);
  const total = segments.reduce((sum, s) => sum + s.value, 0);

  if (total === 0) {
    return <p className="empty-state">{emptyMessage}</p>;
  }

  return (
    <div>
      <div className="stack-bar">
        {segments.map((s, idx) => {
          const pct = (s.value / total) * 100;
          if (pct <= 0) return null;
          const isHovered = hovered === s.key;
          return (
            <div
              key={s.key}
              className="stack-bar-segment"
              style={{
                width: `${pct}%`,
                background: s.color,
                borderLeft: idx > 0 ? "2px solid var(--color-surface)" : undefined,
                filter: isHovered ? "brightness(1.08)" : undefined,
              }}
              tabIndex={0}
              role="img"
              aria-label={`${s.label}: ${s.value} (${pct.toFixed(0)}%)`}
              onMouseEnter={() => setHovered(s.key)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(s.key)}
              onBlur={() => setHovered(null)}
            >
              {pct >= 14 && <span className="stack-bar-label">{s.value}</span>}
              {isHovered && (
                <div className="stack-bar-tooltip">
                  <strong>{s.value}</strong>&nbsp;{s.label} ({pct.toFixed(0)}%)
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="bar-legend">
        {segments.map((s) => (
          <span key={s.key}>
            <i className="legend-dot" style={{ background: s.color }} /> {s.label} {s.value}
          </span>
        ))}
      </div>
    </div>
  );
}
