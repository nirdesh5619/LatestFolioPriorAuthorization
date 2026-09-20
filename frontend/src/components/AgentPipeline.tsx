import { AGENT_PIPELINE_STEPS, type PipelineState } from "../agentPipeline";

const STATUS_ICON: Record<string, string> = {
  pending: "",
  running: "",
  success: "✓",
  error: "✕",
  skipped: "–",
};

interface Props {
  pipeline: PipelineState;
}

export default function AgentPipeline({ pipeline }: Props) {
  return (
    <div className="pipeline">
      {AGENT_PIPELINE_STEPS.map((step, idx) => {
        const state = pipeline[step.agent] ?? { status: "pending" as const };
        return (
          <div key={step.agent} style={{ display: "flex", alignItems: "center" }}>
            <div className={`pipeline-step pipeline-step-${state.status}`}>
              <div className="pipeline-step-index">
                {state.status === "running" ? <span className="pipeline-spinner" /> : STATUS_ICON[state.status] || idx + 1}
              </div>
              <div>
                <div className="pipeline-step-label">{step.label}</div>
                <div className="pipeline-step-desc">{step.description}</div>
                {state.executionTimeMs !== undefined && (
                  <div className="pipeline-step-time">{state.executionTimeMs.toFixed(state.executionTimeMs < 1 ? 3 : 1)} ms</div>
                )}
                {state.status === "running" && <div className="pipeline-step-time">running…</div>}
                {state.status === "skipped" && <div className="pipeline-step-time">skipped</div>}
              </div>
            </div>
            {idx < AGENT_PIPELINE_STEPS.length - 1 && <span className="pipeline-connector">&rarr;</span>}
          </div>
        );
      })}
    </div>
  );
}
