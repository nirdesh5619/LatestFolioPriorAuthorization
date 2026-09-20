class AppError(Exception):
    """Base application error with an HTTP-friendly shape."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, requires_clinician_review: bool = False):
        super().__init__(message)
        self.message = message
        self.requires_clinician_review = requires_clinician_review

    def to_dict(self) -> dict:
        return {
            "error": self.error_code,
            "message": self.message,
            "requires_clinician_review": self.requires_clinician_review,
        }


class PatientNotFoundError(AppError):
    status_code = 404
    error_code = "PATIENT_NOT_FOUND"


class OrchestrationRunNotFoundError(AppError):
    status_code = 404
    error_code = "ORCHESTRATION_RUN_NOT_FOUND"


class InvalidPriorAuthRequestError(AppError):
    status_code = 422
    error_code = "INVALID_REQUEST"


class MissingPatientFieldsError(AppError):
    status_code = 422
    error_code = "MISSING_PATIENT_FIELDS"


class VectorStoreUnavailableError(AppError):
    status_code = 503
    error_code = "VECTOR_STORE_UNAVAILABLE"


class EmbeddingModelUnavailableError(AppError):
    status_code = 503
    error_code = "EMBEDDING_MODEL_UNAVAILABLE"


class DatabaseUnavailableError(AppError):
    status_code = 503
    error_code = "DATABASE_UNAVAILABLE"


class AgentExecutionError(AppError):
    status_code = 500
    error_code = "AGENT_EXECUTION_ERROR"


class InvalidPayloadError(AppError):
    status_code = 400
    error_code = "INVALID_PAYLOAD"


class NoRelevantGuidelineError(AppError):
    status_code = 200
    error_code = "NO_RELEVANT_GUIDELINE"

    def __init__(self, message: str = "No sufficiently relevant synthetic guideline content was found."):
        super().__init__(message, requires_clinician_review=True)
