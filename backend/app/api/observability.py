from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidPayloadError
from app.db.database import get_db
from app.schemas.observability import CostMetrics, ObservabilityMetrics
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/metrics", response_model=ObservabilityMetrics)
def get_metrics(
    period: str = Query("all", description="7d | 30d | month | year | all"),
    db: Session = Depends(get_db),
) -> ObservabilityMetrics:
    """System health, request volume, determination outcomes, per-agent latency/
    reliability, and real LLM token/cost usage - aggregated from the same
    orchestration_runs / agent_outputs audit trail every run already writes to.
    Scoped to a trailing window via `period`; defaults to all-time history.
    """
    try:
        return MetricsService(db).get_metrics(period=period)
    except ValueError as exc:
        raise InvalidPayloadError(str(exc)) from exc


@router.get("/costs", response_model=CostMetrics)
def get_cost_metrics(
    period: str = Query("30d", description="7d | 30d | month | year | custom"),
    start_date: datetime | None = Query(None, description="Required when period=custom."),
    end_date: datetime | None = Query(None, description="Required when period=custom."),
    model: str | None = Query(None, description="Filter to a single LLM model id."),
    db: Session = Depends(get_db),
) -> CostMetrics:
    """Per-execution and aggregate LLM cost for a named window (last 7 days, current month,
    current year, a rolling 30 days) or an explicit custom date range, optionally filtered to
    one model. Backs the observability dashboard's cost filters.
    """
    try:
        return MetricsService(db).get_cost_metrics(
            period=period, start_date=start_date, end_date=end_date, model=model
        )
    except ValueError as exc:
        raise InvalidPayloadError(str(exc)) from exc
