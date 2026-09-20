from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.orchestration import AgentTraceEntry, OrchestrationRunRequest, OrchestrationRunSummary
from app.schemas.response import FinalClinicalResponse
from app.services.orchestration_service import OrchestrationService

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


@router.post("/run", response_model=FinalClinicalResponse)
async def run_orchestration(payload: OrchestrationRunRequest, db: Session = Depends(get_db)) -> FinalClinicalResponse:
    service = OrchestrationService(db)
    return await service.run_orchestration(payload)


@router.post("/run/stream")
async def run_orchestration_stream(payload: OrchestrationRunRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    """Streams newline-delimited JSON: one `{"type": "agent", ...}` event per agent as it
    completes, then one `{"type": "final", ...FinalClinicalResponse}` event. Lets a UI show
    the multi-agent pipeline actually progressing in real time instead of only the end result.

    Input validation (missing patient, empty question) happens before the stream starts, so
    it still surfaces as a normal JSON error response with the correct status code.
    """
    service = OrchestrationService(db)
    generator = await service.prepare_streaming_run(payload)
    return StreamingResponse(generator, media_type="application/x-ndjson")


@router.get("/runs/{run_id}", response_model=OrchestrationRunSummary)
def get_run(run_id: int, db: Session = Depends(get_db)) -> OrchestrationRunSummary:
    return OrchestrationService(db).get_run(run_id)


@router.get("/runs/{run_id}/trace", response_model=list[AgentTraceEntry])
def get_trace(run_id: int, db: Session = Depends(get_db)) -> list[AgentTraceEntry]:
    return OrchestrationService(db).get_trace(run_id)


@router.get("/runs/{run_id}/report.pdf")
def get_report_pdf(run_id: int, db: Session = Depends(get_db)) -> Response:
    """Renders the stored determination (and human review outcome, if any) as a
    downloadable PDF - a rendering of what was already decided and recorded,
    not a new computation."""
    pdf_bytes = OrchestrationService(db).get_report_pdf(run_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="determination_{run_id}.pdf"'},
    )
