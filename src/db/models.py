from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.database import Base


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    features: Mapped[dict] = mapped_column(JSON, nullable=False)

    treatment_probability: Mapped[float] = mapped_column(Float, nullable=False)
    control_probability: Mapped[float] = mapped_column(Float, nullable=False)
    uplift_score: Mapped[float] = mapped_column(Float, nullable=False)

    customer_value: Mapped[float] = mapped_column(Float, nullable=False)
    treatment_cost: Mapped[float] = mapped_column(Float, nullable=False)
    expected_incremental_value: Mapped[float] = mapped_column(Float, nullable=False)
    roi: Mapped[float] = mapped_column(Float, nullable=False)

    recommended_action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    decision_reason: Mapped[list] = mapped_column(JSON, nullable=False)

    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_alias: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)

    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    feedback_logs: Mapped[list["FeedbackLog"]] = relationship(
        back_populates="decision_log",
        cascade="all, delete-orphan",
    )


class FeedbackLog(Base):
    __tablename__ = "feedback_logs"

    feedback_id: Mapped[str] = mapped_column(String, primary_key=True)

    decision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("decision_logs.decision_id"),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)

    observed_outcome: Mapped[int] = mapped_column(Integer, nullable=False)
    simulated_outcome_probability: Mapped[float] = mapped_column(Float, nullable=False)

    customer_value: Mapped[float] = mapped_column(Float, nullable=False)
    treatment_cost: Mapped[float] = mapped_column(Float, nullable=False)
    realized_value: Mapped[float] = mapped_column(Float, nullable=False)

    feedback_delay_days: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision_log: Mapped[DecisionLog] = relationship(back_populates="feedback_logs")


class OperationRun(Base):
    __tablename__ = "operation_runs"

    operation_id: Mapped[str] = mapped_column(String, primary_key=True)
    operation: Mapped[str] = mapped_column(String, index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, index=True, nullable=False)
    command_summary: Mapped[str] = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at = mapped_column(DateTime(timezone=True), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tail: Mapped[str | None] = mapped_column(String, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String, nullable=True)


class OperationAudit(Base):
    __tablename__ = "operation_audits"

    audit_id: Mapped[str] = mapped_column(String, primary_key=True)
    operation_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String, index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    simulation_id: Mapped[str] = mapped_column(String, primary_key=True)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, index=True, nullable=False)
    preset: Mapped[str | None] = mapped_column(String, nullable=True)
    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    artifact_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    artifact_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(String, nullable=True)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    version_id: Mapped[str] = mapped_column(String, primary_key=True)
    version_number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False, index=True, nullable=False)
    parent_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(String, nullable=True)


class PolicyAudit(Base):
    __tablename__ = "policy_audits"

    audit_id: Mapped[str] = mapped_column(String, primary_key=True)
    action: Mapped[str] = mapped_column(String, index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    outcome: Mapped[str] = mapped_column(String, nullable=False)
    source_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    target_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("idx_decision_logs_created_action", DecisionLog.created_at, DecisionLog.recommended_action)
Index("idx_feedback_logs_observed_at", FeedbackLog.observed_at)
Index("idx_feedback_logs_user_outcome", FeedbackLog.user_id, FeedbackLog.observed_outcome)
