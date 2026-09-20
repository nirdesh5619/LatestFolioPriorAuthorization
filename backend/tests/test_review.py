def _submit_request(client, identifier: str = "REVIEW-001") -> int:
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

    run_resp = client.post(
        "/api/v1/orchestration/run",
        json={
            "patient_id": patient_resp.json()["id"],
            "requested_service": "Bariatric surgery",
            "service_category": "surgery",
            "diagnosis_codes": ["E66.01"],
            "prior_treatments_tried": ["supervised weight-management program for 6 months"],
        },
    )
    assert run_resp.status_code == 200
    return run_resp.json()["run_id"]


def test_new_run_appears_in_review_queue(client, db_session):
    run_id = _submit_request(client)

    resp = client.get("/api/v1/review/queue")
    assert resp.status_code == 200
    queue = resp.json()

    entry = next(item for item in queue if item["run_id"] == run_id)
    assert entry["requested_service"] == "Bariatric surgery"
    assert entry["determination"] in ("approved", "denied", "pended")


def test_review_detail_exposes_full_ai_response(client, db_session):
    run_id = _submit_request(client, "REVIEW-002")

    resp = client.get(f"/api/v1/review/{run_id}")
    assert resp.status_code == 200
    detail = resp.json()

    assert detail["review_status"] == "pending_review"
    assert detail["reviewer_name"] is None
    assert detail["ai_response"]["run_id"] == run_id
    assert len(detail["ai_response"]["criteria_evaluated"]) > 0


def test_uphold_review_keeps_ai_determination(client, db_session):
    run_id = _submit_request(client, "REVIEW-003")
    ai_determination = client.get(f"/api/v1/review/{run_id}").json()["ai_response"]["determination"]

    resp = client.post(
        f"/api/v1/review/{run_id}",
        json={"reviewer_name": "Dr. Smith", "decision": "uphold", "notes": "Agree with the AI determination."},
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["decision"] == "upheld"
    assert result["final_determination"] == ai_determination
    assert result["reviewer_name"] == "Dr. Smith"

    # Removed from the queue once reviewed.
    queue = client.get("/api/v1/review/queue").json()
    assert all(item["run_id"] != run_id for item in queue)

    detail = client.get(f"/api/v1/review/{run_id}").json()
    assert detail["review_status"] == "reviewed"
    assert detail["reviewer_decision"] == "upheld"


def test_override_review_replaces_determination(client, db_session):
    run_id = _submit_request(client, "REVIEW-004")

    resp = client.post(
        f"/api/v1/review/{run_id}",
        json={
            "reviewer_name": "Dr. Jones",
            "decision": "override",
            "final_determination": "approved",
            "notes": "Clinical documentation reviewed separately and supports approval.",
        },
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["decision"] == "overridden"
    assert result["final_determination"] == "approved"

    detail = client.get(f"/api/v1/review/{run_id}").json()
    assert detail["reviewer_decision"] == "overridden"
    assert detail["final_determination"] == "approved"


def test_override_without_notes_is_rejected(client, db_session):
    run_id = _submit_request(client, "REVIEW-005")

    resp = client.post(
        f"/api/v1/review/{run_id}",
        json={"reviewer_name": "Dr. Jones", "decision": "override", "final_determination": "approved", "notes": ""},
    )
    assert resp.status_code == 400


def test_override_without_final_determination_is_rejected(client, db_session):
    run_id = _submit_request(client, "REVIEW-006")

    resp = client.post(
        f"/api/v1/review/{run_id}",
        json={"reviewer_name": "Dr. Jones", "decision": "override", "notes": "Some notes."},
    )
    assert resp.status_code == 400


def test_cannot_review_the_same_run_twice(client, db_session):
    run_id = _submit_request(client, "REVIEW-007")

    first = client.post(
        f"/api/v1/review/{run_id}",
        json={"reviewer_name": "Dr. Smith", "decision": "uphold", "notes": "Looks correct."},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/review/{run_id}",
        json={"reviewer_name": "Dr. Smith", "decision": "uphold", "notes": "Looks correct."},
    )
    assert second.status_code == 400


def test_review_detail_not_found(client):
    resp = client.get("/api/v1/review/999999")
    assert resp.status_code == 404


def test_metrics_reflect_review_progress(client, db_session):
    run_a = _submit_request(client, "REVIEW-008")
    _submit_request(client, "REVIEW-009")

    client.post(
        f"/api/v1/review/{run_a}",
        json={
            "reviewer_name": "Dr. Lee",
            "decision": "override",
            "final_determination": "denied",
            "notes": "Insufficient documentation on independent review.",
        },
    )

    metrics = client.get("/api/v1/observability/metrics").json()
    review = metrics["review"]

    assert review["reviewed_count"] >= 1
    assert review["pending_count"] >= 1
    assert review["overridden_count"] >= 1
    assert 0.0 < review["override_rate"] <= 1.0
