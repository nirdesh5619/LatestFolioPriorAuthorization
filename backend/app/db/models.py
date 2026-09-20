from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_identifier: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(32))
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)
    smoking_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    systolic_bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    diastolic_bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cholesterol: Mapped[float | None] = mapped_column(Float, nullable=True)
    ldl: Mapped[float | None] = mapped_column(Float, nullable=True)
    hdl: Mapped[float | None] = mapped_column(Float, nullable=True)
    triglycerides: Mapped[float | None] = mapped_column(Float, nullable=True)
    hba1c: Mapped[float | None] = mapped_column(Float, nullable=True)
    fasting_glucose: Mapped[float | None] = mapped_column(Float, nullable=True)
    medical_history: Mapped[str] = mapped_column(Text, default="[]")
    current_medications: Mapped[str] = mapped_column(Text, default="[]")
    allergies: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    orchestration_runs: Mapped[list["OrchestrationRun"]] = relationship(back_populates="patient")


class Guideline(Base):
    __tablename__ = "guidelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guideline_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    organization: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(32))
    publication_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    condition: Mapped[str] = mapped_column(String(128))
    source_file: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    chunks: Mapped[list["GuidelineChunk"]] = relationship(back_populates="guideline")


class GuidelineChunk(Base):
    __tablename__ = "guideline_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guideline_id: Mapped[int] = mapped_column(ForeignKey("guidelines.id"))
    chunk_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    section: Mapped[str] = mapped_column(String(255))
    page: Mapped[int] = mapped_column(Integer, default=1)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    guideline: Mapped["Guideline"] = relationship(back_populates="chunks")


class OrchestrationRun(Base):
    __tablename__ = "orchestration_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    clinical_question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    final_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Prior-authorization request details
    requested_service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diagnosis_codes: Mapped[str] = mapped_column(Text, default="[]")
    urgency: Mapped[str] = mapped_column(String(32), default="routine")
    prior_treatments_tried: Mapped[str] = mapped_column(Text, default="[]")

    # Determination outcome (as decided by the deterministic agent pipeline)
    determination: Mapped[str | None] = mapped_column(String(32), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_response_json: Mapped[str] = mapped_column(Text, default="{}")

    # Human-in-the-loop review. Every completed run requires a clinical
    # reviewer to uphold or override the AI determination before it is final -
    # this is the actual mechanism behind `requires_clinician_review`, not
    # just a flag with no follow-through.
    review_status: Mapped[str] = mapped_column(String(32), default="pending_review")
    reviewer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewer_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)  # upheld | overridden
    final_determination: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="orchestration_runs")
    agent_outputs: Mapped[list["AgentOutput"]] = relationship(back_populates="run")
    criteria_records: Mapped[list["CriterionRecord"]] = relationship(back_populates="run")


class AgentOutput(Base):
    __tablename__ = "agent_outputs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("orchestration_runs.id"))
    agent_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    input_json: Mapped[str] = mapped_column(Text, default="{}")
    output_json: Mapped[str] = mapped_column(Text, default="{}")
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped["OrchestrationRun"] = relationship(back_populates="agent_outputs")


class CriterionRecord(Base):
    """Durable audit trail of every individual policy criterion evaluated for a
    determination - queryable independently of the per-run JSON trace blobs."""

    __tablename__ = "criteria_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("orchestration_runs.id"))
    criterion: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    patient_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    guideline: Mapped[str] = mapped_column(String(255))
    section: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped["OrchestrationRun"] = relationship(back_populates="criteria_records")
