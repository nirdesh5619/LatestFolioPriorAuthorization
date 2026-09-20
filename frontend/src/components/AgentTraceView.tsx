import type { AgentTraceEntry } from "../api/types";
import { StatusBadge } from "./Badge";

interface Props {
  trace: AgentTraceEntry[];
  /** Label of the agent currently executing on the backend, if any — renders a live "in progress" row. */
  runningAgent?: string | null;
}

export default function AgentTraceView({ trace, runningAgent }: Props) {
  if (trace.length === 0 && !runningAgent) {
    return <p className="empty-state">No agent trace recorded for this run.</p>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="trace-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>Status</th>
            <th>Time</th>
            <th>Input</th>
            <th>Output</th>
          </tr>
        </thead>
        <tbody>
          {trace.map((entry, idx) => (
            <tr key={`${entry.agent}-${idx}`}>
              <td>{entry.agent}</td>
              <td>
                <StatusBadge status={entry.status} />
              </td>
              <td>{entry.execution_time_ms.toFixed(2)} ms</td>
              <td>
                <pre>{JSON.stringify(entry.input, null, 2)}</pre>
              </td>
              <td>
                <pre>{JSON.stringify(entry.output, null, 2)}</pre>
              </td>
            </tr>
          ))}
          {runningAgent && (
            <tr className="trace-row-running">
              <td>{runningAgent}</td>
              <td>
                <span className="badge badge-moderate">running</span>
              </td>
              <td>&hellip;</td>
              <td colSpan={2} className="muted">
                Waiting for this agent to finish on the backend&hellip;
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
