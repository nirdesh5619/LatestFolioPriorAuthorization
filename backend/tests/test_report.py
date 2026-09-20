def _submit_request(client, identifier: str = "REPORT-001") -> int:
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


def test_report_pdf_downloads_for_completed_run(client, db_session):
    run_id = _submit_request(client)

    resp = client.get(f"/api/v1/orchestration/runs/{run_id}/report.pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert f"determination_{run_id}.pdf" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000


def test_report_pdf_includes_review_outcome_once_reviewed(client, db_session):
    run_id = _submit_request(client, "REPORT-002")

    client.post(
        f"/api/v1/review/{run_id}",
        json={
            "reviewer_name": "Dr. Alvarez",
            "decision": "override",
            "final_determination": "approved",
            "notes": "Independent review supports approval.",
        },
    )

    resp = client.get(f"/api/v1/orchestration/runs/{run_id}/report.pdf")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
    assert len(resp.content) > 1000


def test_report_pdf_missing_run_returns_404(client):
    resp = client.get("/api/v1/orchestration/runs/999999/report.pdf")
    assert resp.status_code == 404
