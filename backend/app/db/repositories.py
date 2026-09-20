import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentOutput,
    CriterionRecord,
    Guideline,
    GuidelineChunk,
    OrchestrationRun,
    Patient,
)


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Patient:
        payload = dict(data)
        for field in ("medical_history", "current_medications", "allergies"):
            if field in payload and not isinstance(payload[field], str):
                payload[field] = json.dumps(payload[field])
        patient = Patient(**payload)
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def get(self, patient_id: int) -> Patient | None:
        return self.db.get(Patient, patient_id)

    def get_by_identifier(self, identifier: str) -> Patient | None:
        stmt = select(Patient).where(Patient.patient_identifier == identifier)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, skip: int = 0, limit: int = 100) -> list[Patient]:
        stmt = select(Patient).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        return len(list(self.db.execute(select(Patient)).scalars().all()))


class GuidelineRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Guideline:
        guideline = Guideline(**data)
        self.db.add(guideline)
        self.db.commit()
        self.db.refresh(guideline)
        return guideline

    def get_by_guideline_id(self, guideline_id: str) -> Guideline | None:
        stmt = select(Guideline).where(Guideline.guideline_id == guideline_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self) -> list[Guideline]:
        return list(self.db.execute(select(Guideline)).scalars().all())

    def create_chunk(self, data: dict) -> GuidelineChunk:
        chunk = GuidelineChunk(**data)
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def count_chunks(self) -> int:
        return len(list(self.db.execute(select(GuidelineChunk)).scalars().all()))


class OrchestrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, patient_id: int, clinical_question: str, request_details: dict | None = None) -> OrchestrationRun:
        request_details = request_details or {}
        run = OrchestrationRun(
            patient_id=patient_id,
            clinical_question=clinical_question,
            status="running",
            requested_service=request_details.get("requested_service"),
            service_category=request_details.get("service_category"),
            diagnosis_codes=json.dumps(request_details.get("diagnosis_codes") or []),
            urgency=request_details.get("urgency") or "routine",
            prior_treatments_tried=json.dumps(request_details.get("prior_treatments_tried") or []),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: int) -> OrchestrationRun | None:
        return self.db.get(OrchestrationRun, run_id)

    def complete_run(
        self,
        run: OrchestrationRun,
        status: str,
        final_recommendation: str,
        determination: str | None = None,
        decision_rationale: str | None = None,
        final_response_json: str = "{}",
    ) -> OrchestrationRun:
        from datetime import datetime, timezone

        run.status = status
        run.final_recommendation = final_recommendation
        run.determination = determination
        run.decision_rationale = decision_rationale
        run.final_response_json = final_response_json
        run.review_status = "pending_review"
        run.completed_at = datetime.now(timezone.utc)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def list_all_runs(self) -> list[OrchestrationRun]:
        return list(self.db.execute(select(OrchestrationRun)).scalars().all())

    def list_recent_runs(self, limit: int = 20) -> list[OrchestrationRun]:
        stmt = select(OrchestrationRun).order_by(OrchestrationRun.id.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def list_pending_review(self, limit: int = 50, determination: str = None) -> list[OrchestrationRun]:
        stmt = (
            select(OrchestrationRun)
            .where(OrchestrationRun.review_status == "pending_review")
            .order_by(OrchestrationRun.created_at.asc())
        )
        if determination:
            stmt = stmt.where(OrchestrationRun.determination == determination)
        stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def submit_review(
        self,
        run: OrchestrationRun,
        reviewer_name: str,
        decision: str,
        final_determination: str,
        notes: str,
    ) -> OrchestrationRun:
        from datetime import datetime, timezone

        run.review_status = "reviewed"
        run.reviewer_name = reviewer_name
        run.reviewer_decision = decision
        run.final_determination = final_determination
        run.reviewer_notes = notes
        run.reviewed_at = datetime.now(timezone.utc)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def list_all_agent_outputs(self) -> list[AgentOutput]:
        return list(self.db.execute(select(AgentOutput)).scalars().all())

    def add_agent_output(
        self,
        run_id: int,
        agent_name: str,
        status: str,
        input_data: dict,
        output_data: dict,
        execution_time_ms: float,
    ) -> AgentOutput:
        output = AgentOutput(
            run_id=run_id,
            agent_name=agent_name,
            status=status,
            input_json=json.dumps(input_data, default=str),
            output_json=json.dumps(output_data, default=str),
            execution_time_ms=execution_time_ms,
        )
        self.db.add(output)
        self.db.commit()
        self.db.refresh(output)
        return output

    def get_trace(self, run_id: int) -> list[AgentOutput]:
        stmt = select(AgentOutput).where(AgentOutput.run_id == run_id).order_by(AgentOutput.id)
        return list(self.db.execute(stmt).scalars().all())

    def add_criterion_record(self, run_id: int, data: dict) -> CriterionRecord:
        record = CriterionRecord(run_id=run_id, **data)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_criteria_records(self, run_id: int) -> list[CriterionRecord]:
        stmt = select(CriterionRecord).where(CriterionRecord.run_id == run_id)
        return list(self.db.execute(stmt).scalars().all())
