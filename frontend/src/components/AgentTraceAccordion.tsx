import { useState } from "react";
import type { AgentTraceEntry } from "../api/types";
import { StatusBadge } from "./Badge";

interface Props {
  trace: AgentTraceEntry[];
}

/**
 * Renders each agent's trace entry as its own collapsible section (accordion),
 * rather than one always-expanded table — lets a reviewer scan the six agent
 * names/statuses at a glance and drill into only the one(s) they care about.
 */
export default function AgentTraceAccordion({ trace }: Props) {
  const [openKey, setOpenKey] = useState<string | null>(null);

  if (trace.length === 0) {
    return <p className="empty-state">No agent trace recorded for this run.</p>;
  }

  return (
    <div className="trace-accordion">
      {trace.map((entry, idx) => {
        const key = `${entry.agent}-${idx}`;
        const isOpen = openKey === key;
        return (
          <div className={`trace-accordion-item ${isOpen ? "open" : ""}`} key={key}>
            <button
              type="button"
              className="trace-accordion-header"
              onClick={() => setOpenKey(isOpen ? null : key)}
              aria-expanded={isOpen}
            >
              <span className="trace-accordion-chevron">&#9656;</span>
              <span className="trace-accordion-agent">{entry.agent}</span>
              <StatusBadge status={entry.status} />
              <span className="trace-accordion-time">{entry.execution_time_ms.toFixed(2)} ms</span>
            </button>
            {isOpen && (
              <div className="trace-accordion-body">
                <div className="trace-accordion-col">
                  <div className="label">Input</div>
                  <pre>{JSON.stringify(entry.input, null, 2)}</pre>
                </div>
                <div className="trace-accordion-col">
                  <div className="label">Output</div>
                  <pre>{JSON.stringify(entry.output, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
