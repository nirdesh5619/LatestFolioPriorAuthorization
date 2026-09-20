from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "FolioPrior Auth"
    environment: str = "development"

    database_url: str = "sqlite:///./clinical_guidelines.db"

    faiss_index_path: str = "./vector_store/index.faiss"
    faiss_metadata_path: str = "./vector_store/metadata.json"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    top_k: int = 8
    log_level: str = "INFO"

    guidelines_dir: str = "./data/guidelines"
    patients_seed_file: str = "./data/patients/sample_patients.json"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # --- LLM (determination rationale generation) -------------------------
    # Fully optional: the determination agent falls back to a deterministic,
    # templated rationale when no key is configured, so the platform runs
    # end-to-end with zero external dependencies out of the box.
    # `llm_provider` picks which SDK/key is used for both LLM calls (the
    # rationale and the approval-path scenario suggestion) - "anthropic" or
    # "openai". Only the selected provider's key needs to be set.
    llm_provider: str = "anthropic"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5-20251001"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    llm_max_tokens: int = 500

    # Approximate list pricing used only to *estimate* spend in the
    # observability dashboard - not billing-accurate, illustrative only.
    llm_input_cost_per_million: float = 1.0
    llm_output_cost_per_million: float = 5.0

    @property
    def llm_enabled(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key.strip())
        return bool(self.anthropic_api_key.strip())

    @property
    def llm_model(self) -> str:
        return self.openai_model if self.llm_provider == "openai" else self.anthropic_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
