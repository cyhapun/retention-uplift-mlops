from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException

from src.data.constants import FEATURE_COLS
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

    feature_df = pd.DataFrame([{feature: float(features[feature]) for feature in FEATURE_COLS}])

    return feature_df


def get_model_version(model: Any) -> str:
    metadata = getattr(model, "metadata", None)

    if metadata is None:
        return "unknown"

    run_id = getattr(metadata, "run_id", None)

    if run_id is None:
        return "unknown"

    return str(run_id)


def create_app(model: Any | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
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

        feature_df = validate_features(request.features)

        prediction = app.state.model.predict(feature_df).iloc[0]

        treatment_probability = float(prediction["treatment_probability"])
        control_probability = float(prediction["control_probability"])
        uplift_score = float(prediction["uplift_score"])

        decision = recommend_action_from_policy(
            uplift_score=uplift_score,
            customer_value=request.customer_value,
        )

        return DecisionResponse(
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
            model_version=get_model_version(app.state.model),
        )

    return app


app = create_app()