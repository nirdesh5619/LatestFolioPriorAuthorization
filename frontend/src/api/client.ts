import type {
  AgentTraceEntry,
  ApiErrorBody,
  CostMetrics,
  CostPeriod,
  FinalClinicalResponse,
  GuidelineSearchResponse,
  GuidelineSummary,
  HealthStatus,
  MetricsPeriod,
  ObservabilityMetrics,
  OrchestrationRunSummary,
  OrchestrationStreamEvent,
  Patient,
  PatientCreatePayload,
  PriorAuthRequestPayload,
  ReviewDetail,
  ReviewQueueItem,
  ReviewResult,
  SubmitReviewPayload,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody | null;

  constructor(status: number, message: string, body: ApiErrorBody | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw new ApiError(res.status, body?.message ?? res.statusText, body);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<HealthStatus>("/health"),

  listPatients: () => request<Patient[]>("/patients"),
  getPatient: (id: number) => request<Patient>(`/patients/${id}`),
  createPatient: (payload: PatientCreatePayload) =>
    request<Patient>("/patients", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listGuidelines: () => request<GuidelineSummary[]>("/guidelines"),
  searchGuidelines: (query: string, top_k?: number) =>
    request<GuidelineSearchResponse>("/guidelines/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k }),
    }),

  runOrchestration: (payload: PriorAuthRequestPayload) =>
    request<FinalClinicalResponse>("/orchestration/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getRun: (runId: number) => request<OrchestrationRunSummary>(`/orchestration/runs/${runId}`),
  getTrace: (runId: number) => request<AgentTraceEntry[]>(`/orchestration/runs/${runId}/trace`),
  getReportUrl: (runId: number) => `${API_BASE_URL}/orchestration/runs/${runId}/report.pdf`,

  getMetrics: (period: MetricsPeriod = "all", recentLimit?: number) => {
    const query = new URLSearchParams({ period });
    if (recentLimit) query.set("recent_limit", String(recentLimit));
    return request<ObservabilityMetrics>(`/observability/metrics?${query.toString()}`);
  },
  getCostMetrics: (params: { period: CostPeriod; startDate?: string; endDate?: string; model?: string }) => {
    const query = new URLSearchParams({ period: params.period });
    if (params.startDate) query.set("start_date", params.startDate);
    if (params.endDate) query.set("end_date", params.endDate);
    if (params.model) query.set("model", params.model);
    return request<CostMetrics>(`/observability/costs?${query.toString()}`);
  },

  getReviewQueue: () => request<ReviewQueueItem[]>("/review/queue"),
  getReviewDetail: (runId: number) => request<ReviewDetail>(`/review/${runId}`),
  submitReview: (runId: number, payload: SubmitReviewPayload) =>
    request<ReviewResult>(`/review/${runId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

/**
 * Streams the multi-agent orchestration run as newline-delimited JSON: one
 * event per agent the instant it completes on the backend, then one final
 * event with the full structured response. Lets the UI show the pipeline
 * genuinely progressing in real time instead of only the end result.
 */
export async function* runOrchestrationStream(payload: PriorAuthRequestPayload): AsyncGenerator<OrchestrationStreamEvent> {
  const res = await fetch(`${API_BASE_URL}/orchestration/run/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok || !res.body) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw new ApiError(res.status, body?.message ?? res.statusText, body);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    let newlineIndex: number;
    while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newlineIndex).trim();
      buffer = buffer.slice(newlineIndex + 1);
      if (line) yield JSON.parse(line) as OrchestrationStreamEvent;
    }
  }

  const trailing = buffer.trim();
  if (trailing) yield JSON.parse(trailing) as OrchestrationStreamEvent;
}
