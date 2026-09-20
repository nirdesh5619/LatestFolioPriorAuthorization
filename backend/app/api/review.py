from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.review import ReviewDetail, ReviewQueueItem, ReviewResult, SubmitReviewRequest
from app.services.review_service import ReviewService

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue", response_model=list[ReviewQueueItem])
def get_review_queue(limit: int = 50, db: Session = Depends(get_db)) -> list[ReviewQueueItem]:
    """Every completed determination awaiting a clinical reviewer's sign-off, oldest first."""
    return ReviewService(db).list_queue(limit)


@router.get("/{run_id}", response_model=ReviewDetail)
def get_review_detail(run_id: int, db: Session = Depends(get_db)) -> ReviewDetail:
    return ReviewService(db).get_detail(run_id)


@router.post("/{run_id}", response_model=ReviewResult)
def submit_review(run_id: int, payload: SubmitReviewRequest, db: Session = Depends(get_db)) -> ReviewResult:
    """Records a reviewer's decision: uphold the AI determination as-is, or override it
    with a required rationale. This is the actual human-in-the-loop gate - a run is not
    truly final until this has happened, regardless of what the agents decided."""
    return ReviewService(db).submit_review(run_id, payload)
