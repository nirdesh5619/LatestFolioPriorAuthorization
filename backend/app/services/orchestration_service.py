import json
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.core.exceptions import OrchestrationRunNotFoundError, PatientNotFoundError
from app.db.models import OrchestrationRun
from app.db.repositories import OrchestrationRepository, PatientRepository
from app.orchestration.orchestrator import FinalResponseOrchestrator
from app.orchestration.state import ClinicalWorkflowState, PriorAuthRequest
from app.rag.retriever import GuidelineRetriever
from app.schemas.orchestration import AgentTraceEntry, OrchestrationRunRequest, OrchestrationRunSummary
from app.schemas.patient import PatientRead
from app.schemas.response import FinalClinicalResponse


class OrchestrationService:
    def __init__(self, db: Session, retriever: GuidelineRetriever | None = None):
        self.db = db
        self.patient_repo = PatientRepository(db)
        self.run_repo = OrchestrationRepository(db)
        self.orchestrator = FinalResponseOrchestrator(retriever)

    def _load_patient(self, patient_id: int) -> dict:
        patient_row = self.patient_repo.get(patient_id)
        if patient_row is None:
            raise PatientNotFoundError(f"Patient with id {patient_id} was not found.")
        return PatientRead.from_orm_row(patient_row).model_dump()

    @staticmethod
    def _build_request(payload: OrchestrationRunRequest) -> PriorAuthRequest:
        return PriorAuthRequest(
            requested_service=payload.requested_service,
            service_category=payload.service_category,
            diagnosis_codes=payload.diagnosis_codes,
            urgency=payload.urgency,
            prior_treatments_tried=payload.prior_treatments_tried,
        )

    async def run_orchestration(self, payload: OrchestrationRunRequest) -> FinalClinicalResponse:
        patient_data = self._load_patient(payload.patient_id)
        request = self._build_request(payload)

        run = self.run_repo.create_run(
            patient_id=payload.patient_id,
            clinical_question=payload.clinical_question,
            request_details=payload.model_dump(),
        )

        state = await self.orchestrator.run(patient_data, payload.clinical_question, request)

        for trace in state.trace:
            self.run_repo.add_agent_output(
                run_id=run.id,
                agent_name=trace.agent_name,
                status=trace.status,
                input_data=trace.input_data,
                output_data=trace.output_data,
                execution_time_ms=trace.execution_time_ms,
            )

        final_response = self._finalize_run(run, state)
        return FinalClinicalResponse(**final_response)

    async def prepare_streaming_run(self, payload: OrchestrationRunRequest) -> AsyncIterator[str]:
        """Validates inputs eagerly (so bad requests still get a normal error response),
        then returns an async generator of newline-delimited JSON events: one per agent
        as it completes, followed by a final event with the full structured response.
        """
        patient_data = self._load_patient(payload.patient_id)
        request = self._build_request(payload)

        run = self.run_repo.create_run(
            patient_id=payload.patient_id,
            clinical_question=payload.clinical_question,
            request_details=payload.model_dump(),
        )

        return self._stream_orchestration(run, patient_data, payload.clinical_question, request)

    async def _stream_orchestration(
        self, run: OrchestrationRun, patient_data: dict, clinical_question: str, request: PriorAuthRequest
    ) -> AsyncIterator[str]:
        async for kind, payload in self.orchestrator.run_streaming(patient_data, clinical_question, request):
            if kind == "agent":
                trace = payload
                self.run_repo.add_agent_output(
                    run_id=run.id,
                    agent_name=trace.agent_name,
                    status=trace.status,
                    input_data=trace.input_data,
                    output_data=trace.output_data,
                    execution_time_ms=trace.execution_time_ms,
                )
                yield json.dumps(
                    {
                        "type": "agent",
                        "agent": trace.agent_name,
                        "status": trace.status,
                        "input": trace.input_data,
                        "output": trace.output_data,
                        "execution_time_ms": trace.execution_time_ms,
                    },
                    default=str,
                ) + "\n"
            else:
                state: ClinicalWorkflowState = payload
                final_response = self._finalize_run(run, state)
                yield json.dumps({"type": "final", **final_response}, default=str) + "\n"

    def _finalize_run(self, run: OrchestrationRun, state: ClinicalWorkflowState) -> dict:
        final_response = dict(state.final_response)

        for criterion in final_response.get("criteria_evaluated", []):
            self.run_repo.add_criterion_record(
                run_id=run.id,
                data={
                    "criterion": criterion["criterion"],
                    "status": criterion["status"],
                    "patient_evidence": criterion.get("patient_evidence"),
                    "guideline": criterion["guideline"],
                    "section": criterion["section"],
                    "source": criterion["source"],
                },
            )

        final_response["run_id"] = run.id
        final_response["patient_id"] = run.patient_id

        status = "insufficient_information" if state.halted else "completed"
        self.run_repo.complete_run(
            run,
            status=status,
            final_recommendation=final_response["summary"],
            determination=final_response.get("determination"),
            decision_rationale=final_response.get("decision_rationale"),
            final_response_json=json.dumps(final_response, default=str),
        )
        return final_response

    def get_run(self, run_id: int) -> OrchestrationRunSummary:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise OrchestrationRunNotFoundError(f"Orchestration run {run_id} was not found.")
        return OrchestrationRunSummary(
            run_id=run.id,
            patient_id=run.patient_id,
            status=run.status,
            requested_service=run.requested_service,
            determination=run.determination,
            clinical_question=run.clinical_question,
            created_at=run.created_at,
            completed_at=run.completed_at,
        )

    def get_report_pdf(self, run_id: int) -> bytes:
        from app.core.exceptions import InvalidPayloadError
        from app.services.report_service import generate_determination_report

        run = self.run_repo.get_run(run_id)
        if run is None:
            raise OrchestrationRunNotFoundError(f"Orchestration run {run_id} was not found.")
        if run.final_response_json in (None, "", "{}"):
            raise InvalidPayloadError(f"Run {run_id} has not completed yet - no report is available.")

        patient = self.patient_repo.get(run.patient_id)
        return generate_determination_report(run, patient)

    def get_trace(self, run_id: int) -> list[AgentTraceEntry]:
        run = self.run_repo.get_run(run_id)
        if run is None:
            raise OrchestrationRunNotFoundError(f"Orchestration run {run_id} was not found.")

        entries = self.run_repo.get_trace(run_id)
        return [
            AgentTraceEntry(
                agent=e.agent_name,
                status=e.status,
                input=json.loads(e.input_json),
                output=json.loads(e.output_json),
                execution_time_ms=e.execution_time_ms,
                timestamp=e.created_at,
            )
            for e in entries
        ]
