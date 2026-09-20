from pydantic import BaseModel, Field


class GuidelineSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = None


class GuidelineSearchResult(BaseModel):
    score: float
    text: str
    guideline: str
    guideline_id: str
    section: str
    source: str
    page: int


class GuidelineSearchResponse(BaseModel):
    query: str
    results: list[GuidelineSearchResult]
