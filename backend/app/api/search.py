from fastapi import APIRouter

from app.schemas.guideline import GuidelineSearchRequest, GuidelineSearchResponse
from app.services.guideline_service import GuidelineService

router = APIRouter(prefix="/guidelines", tags=["guidelines"])


@router.post("/search", response_model=GuidelineSearchResponse)
def search_guidelines(payload: GuidelineSearchRequest) -> GuidelineSearchResponse:
    return GuidelineService().search(payload.query, top_k=payload.top_k)
