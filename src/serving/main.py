import os
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from src.data.constants import FEATURE_COLS
from src.db.database import SessionLocal, init_database
from src.db.repository import create_decision_log
from src.policy.decision_engine import recommend_action_from_policy
from src.serving.model_loader import (
    DEFAULT_MODEL_ALIAS,
    DEFAULT_MODEL_NAME,
    build_model_uri,
    load_uplift_model,
)
from src.serving.schemas import (
    DecisionRequest,
    DecisionResponse,
    HealthResponse,
    ModelInfoResponse,
)

from src.serving.metrics import metrics_response, prometheus_middleware, record_decision_metrics

def parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default

    return value.lower() in {"1", "true", "yes", "y"}


def validate_features(features: dict[str, float]) -> pd.DataFrame:
    missing_features = [feature for feature in FEATURE_COLS if feature not in features]

    if missing_features:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required features.",
                "missing_features": missing_features,
            },
        )

    return pd.DataFrame([{feature: float(features[feature]) for feature in FEATURE_COLS}])


def get_model_version(model: Any) -> str:
    metadata = getattr(model, "metadata", None)

    if metadata is None:
        return "unknown"

    run_id = getattr(metadata, "run_id", None)

    if run_id is None:
        return "unknown"

    return str(run_id)


def create_app(
    model: Any | None = None,
    enable_decision_logging: bool | None = None,
) -> FastAPI:
    if enable_decision_logging is None:
        enable_decision_logging = parse_bool(
            os.getenv("ENABLE_DECISION_LOGGING"),
            default=True,
        )
    
    app.middleware("http")(prometheus_middleware)
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.enable_decision_logging = enable_decision_logging

        if app.state.enable_decision_logging:
            init_database()

        if model is not None:
            app.state.model = model
        else:
            app.state.model = load_uplift_model()

        yield

    app = FastAPI(
        title="RetentionOps Decision API",
        description="Uplift-model based decision service for retention actions.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/model-info", response_model=ModelInfoResponse)
    def model_info() -> ModelInfoResponse:
        model_uri = build_model_uri(
            model_name=DEFAULT_MODEL_NAME,
            model_alias=DEFAULT_MODEL_ALIAS,
        )

        return ModelInfoResponse(
            model_name=DEFAULT_MODEL_NAME,
            model_alias=DEFAULT_MODEL_ALIAS,
            model_uri=model_uri,
            model_loaded=hasattr(app.state, "model"),
        )

    @app.post("/decide-action", response_model=DecisionResponse)
    def decide_action(request: DecisionRequest) -> DecisionResponse:
        if not hasattr(app.state, "model"):
            raise HTTPException(status_code=503, detail="Model is not loaded.")

        decision_id = str(uuid4())
        feature_df = validate_features(request.features)

        prediction = app.state.model.predict(feature_df).iloc[0]

        treatment_probability = float(prediction["treatment_probability"])
        control_probability = float(prediction["control_probability"])
        uplift_score = float(prediction["uplift_score"])

        decision = recommend_action_from_policy(
            uplift_score=uplift_score,
            customer_value=request.customer_value,
        )

        model_version = get_model_version(app.state.model)

        response = DecisionResponse(
            decision_id=decision_id,
            user_id=request.user_id,
            treatment_probability=treatment_probability,
            control_probability=control_probability,
            uplift_score=uplift_score,
            customer_value=request.customer_value,
            treatment_cost=float(decision["treatment_cost"]),
            expected_incremental_value=float(decision["expected_incremental_value"]),
            roi=float(decision["roi"]),
            recommended_action=str(decision["recommended_action"]),
            decision_reason=list(decision["decision_reason"]),
            model_name=DEFAULT_MODEL_NAME,
            model_alias=DEFAULT_MODEL_ALIAS,
            model_version=model_version,
        )

        if app.state.enable_decision_logging:
            try:
                with SessionLocal() as session:
                    create_decision_log(
                        session=session,
                        decision_id=response.decision_id,
                        user_id=response.user_id,
                        features=request.features,
                        treatment_probability=response.treatment_probability,
                        control_probability=response.control_probability,
                        uplift_score=response.uplift_score,
                        customer_value=response.customer_value,
                        treatment_cost=response.treatment_cost,
                        expected_incremental_value=response.expected_incremental_value,
                        roi=response.roi,
                        recommended_action=response.recommended_action,
                        decision_reason=response.decision_reason,
                        model_name=response.model_name,
                        model_alias=response.model_alias,
                        model_version=response.model_version,
                    )
            except SQLAlchemyError as exc:
                raise HTTPException(
                    status_code=503,
                    detail=f"Failed to log decision: {exc}",
                ) from exc

        record_decision_metrics(
            recommended_action=response.recommended_action,
            uplift_score=response.uplift_score,
            expected_incremental_value=response.expected_incremental_value,
        )

        return response
    
    @app.get("/metrics")
    def metrics():
        return metrics_response()

    return app


app = create_app()
