import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.repositories import OrchestrationRepository
from app.rag.faiss_store import get_faiss_store
from app.schemas.observability import (
    AgentStats,
    CostByCallType,
    CostFilters,
    CostMetrics,
    CostTimeseriesPoint,
    DeterminationBreakdown,
    LlmUsageStats,
    ObservabilityMetrics,
    RecentRun,
    ReviewStats,
    RunCost,
    SystemHealth,
)

VALID_COST_PERIODS = {"7d", "30d", "month", "year", "custom"}
# The main dashboard has no custom-range picker, just the named windows plus
# "all" (its historical default, unfiltered).
VALID_METRICS_PERIODS = {"7d", "30d", "month", "year", "all"}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(pct * (len(ordered) - 1))))
    return ordered[idx]


def _naive_utc(dt: datetime) -> datetime:
    """Strips tzinfo (after converting to UTC first, if aware) so DB-read timestamps -
    which may come back naive from SQLite regardless of the column's timezone=True - can be
    compared against freshly computed boundaries without raising or silently miscomparing."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _llm_cost(input_tokens: int, output_tokens: int, settings) -> float:
    return (input_tokens / 1_000_000) * settings.llm_input_cost_per_million + (
        output_tokens / 1_000_000
    ) * settings.llm_output_cost_per_million


def _period_bounds(period: str, start_date: datetime | None, end_date: datetime | None) -> tuple[datetime, datetime]:
    """Resolves a named period (or explicit custom range) to naive-UTC [start, end] bounds."""
    now = _naive_utc(datetime.now(timezone.utc))

    if period == "custom":
        if start_date is None or end_date is None:
            raise ValueError("period='custom' requires both start_date and end_date.")
        return _naive_utc(start_date), _naive_utc(end_date)
    if period == "7d":
        return now - timedelta(days=7), now
    if period == "30d":
        return now - timedelta(days=30), now
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now
    if period == "year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0), now
    raise ValueError(f"Unknown period '{period}'. Expected one of {sorted(VALID_COST_PERIODS)}.")


class MetricsService:
    """Aggregates run/agent-output history into the observability dashboard's metrics.

    Reads directly from the existing orchestration_runs / agent_outputs tables -
    no separate metrics store is needed at this scale, and every number here is
    independently reconstructible from that audit trail.
    """

    def __init__(self, db: Session):
        self.db = db
        self.run_repo = OrchestrationRepository(db)

    def get_metrics(self, period: str = "all") -> ObservabilityMetrics:
        """Dashboard-wide metrics, optionally scoped to a trailing window (7d/30d/month/year)
        via `period`; "all" (the default) preserves the original unfiltered, all-time view.
        """
        settings = get_settings()
        if period not in VALID_METRICS_PERIODS:
            raise ValueError(f"Unknown period '{period}'. Expected one of {sorted(VALID_METRICS_PERIODS)}.")

        db_status = "UP"
        try:
            self.db.execute(text("SELECT 1"))
        except Exception:
            db_status = "DOWN"

        vector_status = "UP" if get_faiss_store().exists() else "DOWN"

        runs = self.run_repo.list_all_runs()
        if period != "all":
            start, end = _period_bounds(period, None, None)
            runs = [r for r in runs if start <= _naive_utc(r.created_at) <= end]
        run_ids = {r.id for r in runs}

        agent_outputs = [o for o in self.run_repo.list_all_agent_outputs() if o.run_id in run_ids]

        total_requests = len(runs)
        completed = [r for r in runs if r.status == "completed"]
        insufficient = [r for r in runs if r.status == "insufficient_information"]

        latencies = [
            (r.completed_at - r.created_at).total_seconds() * 1000
            for r in runs
            if r.completed_at is not None
        ]
        avg_latency = sum(latencies) / len(latencies) if latencies else None

        breakdown = DeterminationBreakdown()
        for r in runs:
            if r.determination == "approved":
                breakdown.approved += 1
            elif r.determination == "denied":
                breakdown.denied += 1
            elif r.determination == "pended":
                breakdown.pended += 1
        breakdown.total = breakdown.approved + breakdown.denied + breakdown.pended

        review_rate = 1.0 if completed or insufficient else 0.0
        review_stats = self._review_stats(runs)

        by_agent: dict[str, list] = defaultdict(list)
        for output in agent_outputs:
            by_agent[output.agent_name].append(output)

        agent_stats = []
        for name, outputs in sorted(by_agent.items()):
            times = [o.execution_time_ms for o in outputs]
            agent_stats.append(
                AgentStats(
                    agent=name,
                    total_calls=len(outputs),
                    success_count=sum(1 for o in outputs if o.status == "success"),
                    error_count=sum(1 for o in outputs if o.status == "error"),
                    avg_execution_time_ms=sum(times) / len(times) if times else 0.0,
                    p95_execution_time_ms=_percentile(times, 0.95),
                )
            )

        llm_usage = self._llm_usage_stats(by_agent.get("determination_agent", []), settings)

        recent = sorted(runs, key=lambda r: r.id, reverse=True)[:20]
        recent_runs = [
            RecentRun(
                run_id=r.id,
                patient_id=r.patient_id,
                requested_service=r.requested_service,
                determination=r.determination,
                status=r.status,
                created_at=r.created_at,
            )
            for r in recent
        ]

        return ObservabilityMetrics(
            health=SystemHealth(
                database=db_status,
                vector_store=vector_status,
                llm_configured=settings.llm_enabled,
                llm_provider=settings.llm_provider,
            ),
            total_requests=total_requests,
            completed_requests=len(completed),
            insufficient_information_requests=len(insufficient),
            avg_end_to_end_latency_ms=avg_latency,
            determination_breakdown=breakdown,
            requires_clinician_review_rate=review_rate,
            review=review_stats,
            agent_stats=agent_stats,
            llm_usage=llm_usage,
            recent_runs=recent_runs,
            generated_at=datetime.now(timezone.utc),
        )

    def get_cost_metrics(
        self,
        period: str = "30d",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        model: str | None = None,
    ) -> CostMetrics:
        """Cost per execution and aggregate spend for a named window (last 7 days, current
        month, current year, a rolling 30 days) or an explicit custom date range, optionally
        filtered to a single model. Reuses the same orchestration_runs / agent_outputs audit
        trail as get_metrics() - there is no separate cost ledger to keep in sync.
        """
        settings = get_settings()
        if period not in VALID_COST_PERIODS:
            raise ValueError(f"Unknown period '{period}'. Expected one of {sorted(VALID_COST_PERIODS)}.")

        start, end = _period_bounds(period, start_date, end_date)

        runs = self.run_repo.list_all_runs()
        runs_in_range = {r.id: r for r in runs if start <= _naive_utc(r.created_at) <= end}
        agent_outputs = self.run_repo.list_all_agent_outputs()

        by_call_type: dict[str, CostByCallType] = {
            "rationale": CostByCallType(call_type="rationale"),
            "scenario_suggestion": CostByCallType(call_type="scenario_suggestion"),
        }
        per_run_cost: dict[int, dict] = defaultdict(lambda: {"cost_usd": 0.0, "tokens": 0, "calls": 0})
        bucket_by_month = (end - start).days > 62
        timeseries_buckets: dict[str, dict] = defaultdict(lambda: {"cost_usd": 0.0, "calls": 0, "tokens": 0})

        for output in agent_outputs:
            run = runs_in_range.get(output.run_id)
            if run is None or output.agent_name != "determination_agent":
                continue

            try:
                data = json.loads(output.output_json)
            except (json.JSONDecodeError, TypeError):
                continue

            for key, call_type in (("llm_usage", "rationale"), ("scenario_llm_usage", "scenario_suggestion")):
                usage = data.get(key)
                if not usage:
                    continue
                if model and usage.get("model") != model:
                    continue

                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                tokens = input_tokens + output_tokens
                cost = _llm_cost(input_tokens, output_tokens, settings)

                bucket = by_call_type[call_type]
                bucket.calls += 1
                bucket.input_tokens += input_tokens
                bucket.output_tokens += output_tokens
                bucket.cost_usd += cost

                per_run_cost[run.id]["cost_usd"] += cost
                per_run_cost[run.id]["tokens"] += tokens
                per_run_cost[run.id]["calls"] += 1

                bucket_date = _naive_utc(run.created_at)
                bucket_key = bucket_date.strftime("%Y-%m") if bucket_by_month else bucket_date.strftime("%Y-%m-%d")
                timeseries_buckets[bucket_key]["cost_usd"] += cost
                timeseries_buckets[bucket_key]["calls"] += 1
                timeseries_buckets[bucket_key]["tokens"] += tokens

        for bucket in by_call_type.values():
            bucket.cost_usd = round(bucket.cost_usd, 6)

        total_cost = sum(b.cost_usd for b in by_call_type.values())
        total_calls = sum(b.calls for b in by_call_type.values())
        total_tokens = sum(b.input_tokens + b.output_tokens for b in by_call_type.values())

        per_run = [
            RunCost(
                run_id=run_id,
                requested_service=runs_in_range[run_id].requested_service,
                determination=runs_in_range[run_id].determination,
                created_at=runs_in_range[run_id].created_at,
                cost_usd=round(v["cost_usd"], 6),
                tokens=v["tokens"],
                calls=v["calls"],
            )
            for run_id, v in per_run_cost.items()
        ]
        per_run.sort(key=lambda r: r.created_at, reverse=True)

        timeseries = [
            CostTimeseriesPoint(date=k, cost_usd=round(v["cost_usd"], 6), calls=v["calls"], tokens=v["tokens"])
            for k, v in sorted(timeseries_buckets.items())
        ]

        executions_in_range = len(runs_in_range)

        return CostMetrics(
            filters=CostFilters(period=period, start_date=start, end_date=end, model=model),
            total_cost_usd=round(total_cost, 6),
            total_calls=total_calls,
            total_tokens=total_tokens,
            avg_cost_per_execution=round(total_cost / executions_in_range, 6) if executions_in_range else 0.0,
            by_call_type=list(by_call_type.values()),
            timeseries=timeseries,
            per_run=per_run,
            generated_at=datetime.now(timezone.utc),
        )

    def _review_stats(self, runs: list) -> ReviewStats:
        pending = [r for r in runs if r.review_status == "pending_review"]
        reviewed = [r for r in runs if r.review_status == "reviewed"]
        upheld = [r for r in reviewed if r.reviewer_decision == "upheld"]
        overridden = [r for r in reviewed if r.reviewer_decision == "overridden"]

        review_times = [
            (r.reviewed_at - r.completed_at).total_seconds() * 1000
            for r in reviewed
            if r.reviewed_at is not None and r.completed_at is not None
        ]

        return ReviewStats(
            pending_count=len(pending),
            reviewed_count=len(reviewed),
            upheld_count=len(upheld),
            overridden_count=len(overridden),
            override_rate=round(len(overridden) / len(reviewed), 4) if reviewed else 0.0,
            avg_time_to_review_ms=sum(review_times) / len(review_times) if review_times else None,
        )

    def _llm_usage_stats(self, determination_outputs: list, settings) -> LlmUsageStats:
        total_calls = 0
        total_input = 0
        total_output = 0
        fallback_count = 0
        model_used: str | None = None

        now = _naive_utc(datetime.now(timezone.utc))
        week_ago = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        cost_7d = cost_month = cost_year = 0.0

        for output in determination_outputs:
            try:
                data = json.loads(output.output_json)
            except (json.JSONDecodeError, TypeError):
                continue

            created_at = _naive_utc(output.created_at) if output.created_at else None

            usages = []
            rationale_usage = data.get("llm_usage")
            if rationale_usage:
                usages.append(rationale_usage)
            elif data.get("rationale_source") == "template":
                fallback_count += 1

            scenario_usage = data.get("scenario_llm_usage")
            if scenario_usage:
                usages.append(scenario_usage)

            for usage in usages:
                total_calls += 1
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)
                model_used = usage.get("model", model_used)

                cost = _llm_cost(usage.get("input_tokens", 0), usage.get("output_tokens", 0), settings)
                if created_at is not None:
                    if created_at >= week_ago:
                        cost_7d += cost
                    if created_at >= month_start:
                        cost_month += cost
                    if created_at >= year_start:
                        cost_year += cost

        total_tokens = total_input + total_output
        estimated_cost = _llm_cost(total_input, total_output, settings)

        return LlmUsageStats(
            enabled=settings.llm_enabled,
            model=model_used or (settings.llm_model if settings.llm_enabled else None),
            total_calls=total_calls,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_tokens,
            estimated_cost_usd=round(estimated_cost, 6),
            avg_tokens_per_call=round(total_tokens / total_calls, 1) if total_calls else 0.0,
            fallback_count=fallback_count,
            cost_last_7_days_usd=round(cost_7d, 6),
            cost_this_month_usd=round(cost_month, 6),
            cost_this_year_usd=round(cost_year, 6),
        )
