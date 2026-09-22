from datetime import datetime

from pydantic import BaseModel, Field


class AgentStats(BaseModel):
    agent: str
    total_calls: int
    success_count: int
    error_count: int
    avg_execution_time_ms: float
    p95_execution_time_ms: float


class DeterminationBreakdown(BaseModel):
    approved: int = 0
    denied: int = 0
    pended: int = 0
    total: int = 0


class LlmUsageStats(BaseModel):
    enabled: bool
    model: str | None = None
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    avg_tokens_per_call: float = 0.0
    fallback_count: int = 0
    # Quick-glance spend windows, all as of `generated_at` - independent of any
    # filter applied on the dedicated /observability/costs endpoint.
    cost_last_7_days_usd: float = 0.0
    cost_this_month_usd: float = 0.0
    cost_this_year_usd: float = 0.0


class SystemHealth(BaseModel):
    database: str
    vector_store: str
    llm_configured: bool
    llm_provider: str


class RecentRun(BaseModel):
    run_id: int
    patient_id: int
    patient_identifier: str | None = None
    requested_service: str | None
    determination: str | None
    final_determination: str | None = None
    review_status: str
    status: str
    created_at: datetime


class ReviewStats(BaseModel):
    pending_count: int = 0
    reviewed_count: int = 0
    upheld_count: int = 0
    overridden_count: int = 0
    override_rate: float = 0.0
    avg_time_to_review_ms: float | None = None


class CostByCallType(BaseModel):
    call_type: str  # "rationale" | "scenario_suggestion"
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class CostTimeseriesPoint(BaseModel):
    date: str  # ISO date (day- or month-bucketed, depending on the range span)
    cost_usd: float
    calls: int
    tokens: int


class RunCost(BaseModel):
    run_id: int
    requested_service: str | None
    determination: str | None
    created_at: datetime
    cost_usd: float
    tokens: int
    calls: int


class CostFilters(BaseModel):
    period: str  # "7d" | "30d" | "month" | "year" | "custom"
    start_date: datetime
    end_date: datetime
    model: str | None = None


class CostMetrics(BaseModel):
    filters: CostFilters
    total_cost_usd: float = 0.0
    total_calls: int = 0
    total_tokens: int = 0
    avg_cost_per_execution: float = 0.0
    by_call_type: list[CostByCallType] = Field(default_factory=list)
    timeseries: list[CostTimeseriesPoint] = Field(default_factory=list)
    per_run: list[RunCost] = Field(default_factory=list)
    generated_at: datetime


class ObservabilityMetrics(BaseModel):
    health: SystemHealth
    total_requests: int
    completed_requests: int
    insufficient_information_requests: int
    avg_end_to_end_latency_ms: float | None = None
    determination_breakdown: DeterminationBreakdown
    requires_clinician_review_rate: float
    review: ReviewStats
    agent_stats: list[AgentStats] = Field(default_factory=list)
    llm_usage: LlmUsageStats
    recent_runs: list[RecentRun] = Field(default_factory=list)
    generated_at: datetime
