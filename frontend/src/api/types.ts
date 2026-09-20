export interface Patient {
  id: number;
  patient_identifier: string;
  age: number;
  gender: string;
  weight_kg: number | null;
  height_cm: number | null;
  bmi: number | null;
  smoking_status: string | null;
  systolic_bp: number | null;
  diastolic_bp: number | null;
  heart_rate: number | null;
  total_cholesterol: number | null;
  ldl: number | null;
  hdl: number | null;
  triglycerides: number | null;
  hba1c: number | null;
  fasting_glucose: number | null;
  medical_history: string[];
  current_medications: string[];
  allergies: string[];
  created_at: string;
  updated_at: string;
}

export type PatientCreatePayload = Omit<Patient, "id" | "created_at" | "updated_at">;

export interface GuidelineEvidence {
  guideline: string;
  guideline_id: string;
  section: string;
  evidence: string;
  relevance_score: number;
  source: string;
}

export type DeterminationStatus = "approved" | "denied" | "pended";
export type CriterionStatus = "MET" | "NOT_MET" | "UNKNOWN";

export interface CriterionEvaluation {
  criterion: string;
  status: CriterionStatus;
  patient_evidence: string | null;
  guideline: string;
  section: string;
  source: string;
}

export interface LlmUsageInfo {
  model: string;
  input_tokens: number;
  output_tokens: number;
}

export interface PriorAuthRequestPayload {
  patient_id: number;
  requested_service: string;
  service_category: string;
  diagnosis_codes: string[];
  urgency: string;
  prior_treatments_tried: string[];
  clinical_question?: string;
}

export interface FinalClinicalResponse {
  run_id: number;
  patient_id: number;
  summary: string;

  requested_service: string | null;
  determination: DeterminationStatus | null;
  decision_rationale: string | null;
  llm_usage: LlmUsageInfo | null;
  approval_path_suggestion: string | null;
  scenario_llm_usage: LlmUsageInfo | null;

  identified_conditions: string[];
  risk_factors: string[];
  risk_category: string | null;
  missing_information: string[];

  guideline_evidence: GuidelineEvidence[];
  criteria_evaluated: CriterionEvaluation[];

  safety_flags: string[];
  requires_clinician_review: boolean;
  disclaimer: string;
}

export interface OrchestrationRunSummary {
  run_id: number;
  patient_id: number;
  status: string;
  requested_service: string | null;
  determination: DeterminationStatus | null;
  clinical_question: string;
  created_at: string;
  completed_at: string | null;
}

export interface AgentTraceEntry {
  agent: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  execution_time_ms: number;
  timestamp: string;
}

export interface GuidelineSearchResult {
  score: number;
  text: string;
  guideline: string;
  guideline_id: string;
  section: string;
  source: string;
  page: number;
}

export interface GuidelineSearchResponse {
  query: string;
  results: GuidelineSearchResult[];
}

export interface GuidelineSummary {
  guideline_id: string;
  title: string;
  organization: string;
  version: string;
  condition: string;
  source_file: string;
}

export interface HealthStatus {
  status: string;
  database: string;
  vector_store: string;
}

export interface ApiErrorBody {
  error: string;
  message: string;
  requires_clinician_review: boolean;
}

export interface AgentStreamEvent {
  type: "agent";
  agent: string;
  status: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  execution_time_ms: number;
}

export type FinalStreamEvent = { type: "final" } & FinalClinicalResponse;

export type OrchestrationStreamEvent = AgentStreamEvent | FinalStreamEvent;

// --- Observability -----------------------------------------------------

export interface AgentStats {
  agent: string;
  total_calls: number;
  success_count: number;
  error_count: number;
  avg_execution_time_ms: number;
  p95_execution_time_ms: number;
}

export interface DeterminationBreakdown {
  approved: number;
  denied: number;
  pended: number;
  total: number;
}

export interface LlmUsageStats {
  enabled: boolean;
  model: string | null;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  avg_tokens_per_call: number;
  fallback_count: number;
  cost_last_7_days_usd: number;
  cost_this_month_usd: number;
  cost_this_year_usd: number;
}

export interface SystemHealth {
  database: string;
  vector_store: string;
  llm_configured: boolean;
  llm_provider: string;
}

export interface RecentRun {
  run_id: number;
  patient_id: number;
  requested_service: string | null;
  determination: DeterminationStatus | null;
  status: string;
  created_at: string;
}

export interface ReviewStats {
  pending_count: number;
  reviewed_count: number;
  upheld_count: number;
  overridden_count: number;
  override_rate: number;
  avg_time_to_review_ms: number | null;
}

export interface ObservabilityMetrics {
  health: SystemHealth;
  total_requests: number;
  completed_requests: number;
  insufficient_information_requests: number;
  avg_end_to_end_latency_ms: number | null;
  determination_breakdown: DeterminationBreakdown;
  requires_clinician_review_rate: number;
  review: ReviewStats;
  agent_stats: AgentStats[];
  llm_usage: LlmUsageStats;
  recent_runs: RecentRun[];
  generated_at: string;
}

export type CostPeriod = "7d" | "30d" | "month" | "year" | "custom";
export type MetricsPeriod = "7d" | "30d" | "month" | "year" | "all";
export type LlmCallType = "rationale" | "scenario_suggestion";

export interface CostByCallType {
  call_type: LlmCallType;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface CostTimeseriesPoint {
  date: string;
  cost_usd: number;
  calls: number;
  tokens: number;
}

export interface RunCost {
  run_id: number;
  requested_service: string | null;
  determination: DeterminationStatus | null;
  created_at: string;
  cost_usd: number;
  tokens: number;
  calls: number;
}

export interface CostFilters {
  period: CostPeriod;
  start_date: string;
  end_date: string;
  model: string | null;
}

export interface CostMetrics {
  filters: CostFilters;
  total_cost_usd: number;
  total_calls: number;
  total_tokens: number;
  avg_cost_per_execution: number;
  by_call_type: CostByCallType[];
  timeseries: CostTimeseriesPoint[];
  per_run: RunCost[];
  generated_at: string;
}

// --- Human-in-the-loop review --------------------------------------------

export interface ReviewQueueItem {
  run_id: number;
  patient_id: number;
  patient_identifier: string | null;
  requested_service: string | null;
  determination: DeterminationStatus | null;
  urgency: string;
  status: string;
  created_at: string;
}

export interface ReviewDetail {
  run_id: number;
  patient_id: number;
  review_status: "pending_review" | "reviewed";
  ai_response: FinalClinicalResponse;
  reviewer_name: string | null;
  reviewer_decision: "upheld" | "overridden" | null;
  final_determination: DeterminationStatus | null;
  reviewer_notes: string | null;
  reviewed_at: string | null;
}

export interface SubmitReviewPayload {
  reviewer_name: string;
  decision: "uphold" | "override";
  final_determination?: DeterminationStatus;
  notes: string;
}

export interface ReviewResult {
  run_id: number;
  review_status: string;
  reviewer_name: string;
  decision: string;
  final_determination: string;
  notes: string;
  reviewed_at: string;
}
