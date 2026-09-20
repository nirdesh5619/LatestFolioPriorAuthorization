import json

from sqlalchemy.orm import Session

from app.core.exceptions import InvalidPayloadError, OrchestrationRunNotFoundError
from app.db.repositories import OrchestrationRepository, PatientRepository
from app.schemas.review import ReviewDetail, ReviewQueueItem, ReviewResult, SubmitReviewRequest
from app.schemas.response import FinalClinicalResponse


class ReviewService:
    """The actual human-in-the-loop mechanism behind `requires_clinician_review`.

    Every completed run - approved, denied, or pended - lands in the review
    queue. A reviewer either upholds the AI's determination or overrides it
    with a required rationale; either way the decision is durably recorded
    and the run is removed from the queue exactly once.
    """

    def __init__(self, db: Session):
        self.db = db
        self.run_repo = OrchestrationRepository(db)
        self.patient_repo = PatientRepository(db)

    def list_queue(self, limit: int = 50, determination: str = None) -> list[ReviewQueueItem]:
        runs = self.run_repo.list_pending_review(limit, determination)
        items = []
        for run in runs:
            patient = self.patient_repo.get(run.patient_id)
            items.append(
                ReviewQueueItem(
                    run_id=run.id,
                    patient_id=run.patient_id,
                    patient_identifier=patient.patient_identifier if patient else None,
                    requested_service=run.requested_service,
                    determination=run.determination,
                    urgency=run.urgency,
                    status=run.status,
                    created_at=run.created_at,
                )
            )
        return items

    def get_detail(self, run_id: int) -> ReviewDetail:
        run = self._get_run_or_404(run_id)
        ai_response = json.loads(run.final_response_json or "{}")

        return ReviewDetail(
            run_id=run.id,
            patient_id=run.patient_id,
            review_status=run.review_status,
            ai_response=FinalClinicalResponse(**ai_response),
            reviewer_name=run.reviewer_name,
            reviewer_decision=run.reviewer_decision,
            final_determination=run.final_determination,
            reviewer_notes=run.reviewer_notes,
            reviewed_at=run.reviewed_at,
        )

    def submit_review(self, run_id: int, payload: SubmitReviewRequest) -> ReviewResult:
        run = self._get_run_or_404(run_id)

        if run.review_status == "reviewed":
            raise InvalidPayloadError(f"Run {run_id} has already been reviewed and cannot be reviewed again.")

        if payload.decision == "override" and not payload.final_determination:
            raise InvalidPayloadError("final_determination is required when overriding the AI determination.")

        if payload.decision == "override" and not payload.notes.strip():
            raise InvalidPayloadError("notes are required when overriding the AI determination.")

        final_determination = (
            payload.final_determination if payload.decision == "override" else (run.determination or "pended")
        )
        reviewer_decision = "overridden" if payload.decision == "override" else "upheld"

        updated = self.run_repo.submit_review(
            run,
            reviewer_name=payload.reviewer_name.strip(),
            decision=reviewer_decision,
            final_determination=final_determination,
            notes=payload.notes.strip(),
        )

        return ReviewResult(
            run_id=updated.id,
            review_status=updated.review_status,
            reviewer_name=updated.reviewer_name,
            decision=updated.reviewer_decision,
            final_determination=updated.final_determination,
            notes=updated.reviewer_notes or "",
            reviewed_at=updated.reviewed_at,
        )

    def _get_run_or_404(self, run_id: int):
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise OrchestrationRunNotFoundError(f"Orchestration run {run_id} was not found.")
        return run
