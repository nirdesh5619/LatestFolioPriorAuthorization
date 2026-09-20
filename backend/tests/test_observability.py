from app.services.metrics_service import MetricsService


def _run_one_request(client, identifier: str = "OBS-001") -> int:
    patient_resp = client.post(
        "/api/v1/patients",
        json={
            "patient_identifier": identifier,
            "age": 45,
            "gender": "female",
            "bmi": 42.0,
            "systolic_bp": 128,
            "diastolic_bp": 82,
            "total_cholesterol": 210,
            "ldl": 130,
            "hdl": 48,
            "hba1c": 5.6,
            "fasting_glucose": 98,
            "medical_history": ["obesity"],
        },
    )
    assert patient_resp.status_code == 201
    patient_id = patient_resp.json()["id"]

    run_resp = client.post(
        "/api/v1/orchestration/run",
        json={
            "patient_id": patient_id,
            "requested_service": "Bariatric surgery",
            "service_category": "surgery",
            "diagnosis_codes": ["E66.01"],
            "prior_treatments_tried": ["supervised weight-management program for 6 months"],
        },
    )
    assert run_resp.status_code == 200
    return run_resp.json()["run_id"]


def test_metrics_endpoint_reflects_completed_run(client, db_session):
    _run_one_request(client)

    resp = client.get("/api/v1/observability/metrics")
    assert resp.status_code == 200
    body = resp.json()

    assert body["health"]["database"] == "UP"
    assert body["total_requests"] >= 1
    assert body["determination_breakdown"]["total"] >= 1
    assert body["requires_clinician_review_rate"] == 1.0
    assert len(body["agent_stats"]) == 6
    assert body["llm_usage"]["enabled"] is False  # no API key configured in tests
    assert body["llm_usage"]["total_calls"] == 0
    assert len(body["recent_runs"]) >= 1


def test_metrics_service_aggregates_agent_stats(client, db_session):
    _run_one_request(client, "OBS-002")
    _run_one_request(client, "OBS-003")

    metrics = MetricsService(db_session).get_metrics()

    intake_stats = next(a for a in metrics.agent_stats if a.agent == "clinical_intake_agent")
    assert intake_stats.total_calls == 2
    assert intake_stats.success_count == 2
    assert intake_stats.error_count == 0
    assert intake_stats.avg_execution_time_ms >= 0


def test_metrics_service_handles_empty_history(db_session):
    metrics = MetricsService(db_session).get_metrics()

    assert metrics.total_requests == 0
    assert metrics.determination_breakdown.total == 0
    assert metrics.avg_end_to_end_latency_ms is None
    assert metrics.agent_stats == []
    assert metrics.llm_usage.total_calls == 0
    assert metrics.llm_usage.cost_last_7_days_usd == 0.0
    assert metrics.llm_usage.cost_this_month_usd == 0.0
    assert metrics.llm_usage.cost_this_year_usd == 0.0


def test_cost_metrics_endpoint_default_period(client, db_session):
    _run_one_request(client, "OBS-COST-001")

    resp = client.get("/api/v1/observability/costs")
    assert resp.status_code == 200
    body = resp.json()

    assert body["filters"]["period"] == "30d"
    # No API key configured in tests -> deterministic fallback, zero LLM cost/calls.
    assert body["total_cost_usd"] == 0.0
    assert body["total_calls"] == 0
    assert len(body["by_call_type"]) == 2
    assert {c["call_type"] for c in body["by_call_type"]} == {"rationale", "scenario_suggestion"}
    # The run itself still counts as an execution even with zero LLM spend.
    assert body["avg_cost_per_execution"] == 0.0


def test_cost_metrics_endpoint_named_periods(client, db_session):
    _run_one_request(client, "OBS-COST-002")

    for period in ("7d", "30d", "month", "year"):
        resp = client.get(f"/api/v1/observability/costs?period={period}")
        assert resp.status_code == 200, period
        assert resp.json()["filters"]["period"] == period


def test_cost_metrics_endpoint_custom_period_requires_dates(client, db_session):
    resp = client.get("/api/v1/observability/costs?period=custom")
    assert resp.status_code == 400

    resp = client.get(
        "/api/v1/observability/costs",
        params={"period": "custom", "start_date": "2020-01-01T00:00:00", "end_date": "2020-01-31T00:00:00"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["per_run"] == []  # the run created above falls outside this range


def test_cost_metrics_endpoint_rejects_unknown_period(client, db_session):
    resp = client.get("/api/v1/observability/costs?period=bogus")
    assert resp.status_code == 400


def test_metrics_endpoint_named_periods(client, db_session):
    _run_one_request(client, "OBS-PERIOD-001")

    for period in ("7d", "30d", "month", "year", "all"):
        resp = client.get(f"/api/v1/observability/metrics?period={period}")
        assert resp.status_code == 200, period
        assert resp.json()["total_requests"] >= 1

    resp = client.get("/api/v1/observability/metrics?period=custom")
    assert resp.status_code == 400


def test_metrics_endpoint_period_excludes_out_of_range_runs(client, db_session):
    from datetime import datetime, timedelta, timezone

    run_id = _run_one_request(client, "OBS-PERIOD-002")

    from app.db.repositories import OrchestrationRepository

    run = OrchestrationRepository(db_session).get_run(run_id)
    run.created_at = datetime.now(timezone.utc) - timedelta(days=400)
    db_session.add(run)
    db_session.commit()

    resp = client.get("/api/v1/observability/metrics?period=year")
    assert resp.status_code == 200
    assert all(r["run_id"] != run_id for r in resp.json()["recent_runs"])

    resp = client.get("/api/v1/observability/metrics?period=all")
    assert resp.status_code == 200
    assert any(r["run_id"] == run_id for r in resp.json()["recent_runs"])
