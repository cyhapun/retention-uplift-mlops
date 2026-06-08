from sqlalchemy import JSON, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column
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


Index("idx_decision_logs_created_action", DecisionLog.created_at, DecisionLog.recommended_action)
