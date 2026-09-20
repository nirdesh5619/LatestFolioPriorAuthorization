import type { AgentStreamEvent } from "./api/types";

export type StepStatus = "pending" | "running" | "success" | "error" | "skipped";

export interface StepState {
  status: StepStatus;
  executionTimeMs?: number;
}

export type PipelineState = Record<string, StepState>;

export interface PipelineStepDef {
  agent: string;
  label: string;
  description: string;
}

// Canonical agent order, mirroring backend/app/orchestration/workflow.py — the
// single source of truth for which agents run and in what sequence.
export const AGENT_PIPELINE_STEPS: PipelineStepDef[] = [
  {
    agent: "clinical_intake_agent",
    label: "Clinical Intake",
    description: "Validates patient data & extracts key facts",
  },
  {
    agent: "guideline_retrieval_agent",
    label: "Guideline Retrieval",
    description: "Searches the FAISS index for relevant guideline evidence",
  },
  {
    agent: "risk_stratification_agent",
    label: "Risk Stratification",
    description: "Classifies cardiometabolic & cardiovascular risk factors",
  },
  {
    agent: "criteria_matching_agent",
    label: "Criteria Matching",
    description: "Evaluates each policy criterion as MET / NOT MET / UNKNOWN",
  },
  {
    agent: "determination_agent",
    label: "Determination",
    description: "Decides approve/deny/pend and drafts the rationale",
  },
  {
    agent: "safety_validation_agent",
    label: "Safety Validation",
    description: "Re-verifies evidence and flags missing/unsupported claims",
  },
];

export function buildInitialPipeline(): PipelineState {
  const state: PipelineState = {};
  AGENT_PIPELINE_STEPS.forEach((step, idx) => {
    state[step.agent] = { status: idx === 0 ? "running" : "pending" };
  });
  return state;
}

export function applyAgentEvent(prev: PipelineState, event: AgentStreamEvent): PipelineState {
  const next: PipelineState = { ...prev };
  next[event.agent] = {
    status: event.status === "success" ? "success" : "error",
    executionTimeMs: event.execution_time_ms,
  };

  const idx = AGENT_PIPELINE_STEPS.findIndex((s) => s.agent === event.agent);
  const nextStep = idx >= 0 ? AGENT_PIPELINE_STEPS[idx + 1] : undefined;
  if (nextStep) {
    next[nextStep.agent] = { status: "running" };
  }

  return next;
}

export function finalizePipeline(prev: PipelineState): PipelineState {
  const next: PipelineState = { ...prev };
  AGENT_PIPELINE_STEPS.forEach((step) => {
    const current = next[step.agent];
    if (!current || current.status === "pending" || current.status === "running") {
      next[step.agent] = { status: "skipped" };
    }
  });
  return next;
}
