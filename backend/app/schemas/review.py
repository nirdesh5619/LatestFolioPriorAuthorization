from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.response import FinalClinicalResponse


class ReviewQueueItem(BaseModel):
    run_id: int
    patient_id: int
    patient_identifier: str | None = None
    requested_service: str | None = None
    determination: str | None = None
    urgency: str
    status: str
    created_at: datetime


class ReviewDetail(BaseModel):
    run_id: int
    patient_id: int
    review_status: str  # pending_review | reviewed
    ai_response: FinalClinicalResponse
    reviewer_name: str | None = None
    reviewer_decision: str | None = None  # upheld | overridden
    final_determination: str | None = None
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None


class SubmitReviewRequest(BaseModel):
    reviewer_name: str = Field(min_length=1)
    decision: Literal["uphold", "override"]
    final_determination: Literal["approved", "denied", "pended"] | None = None
    notes: str = Field(default="")


class ReviewResult(BaseModel):
    run_id: int
    review_status: str
    reviewer_name: str
    decision: str
    final_determination: str
    notes: str
    reviewed_at: datetime
