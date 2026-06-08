from pydantic import BaseModel, Field


class DecisionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    features: dict[str, float]
    customer_value: float = Field(gt=0)


class DecisionResponse(BaseModel):
    user_id: str
    treatment_probability: float
    control_probability: float
    uplift_score: float
    customer_value: float
    treatment_cost: float
    expected_incremental_value: float
    roi: float
    recommended_action: str
    decision_reason: list[str]
    model_name: str
    model_alias: str
    model_version: str


class HealthResponse(BaseModel):
    status: str


class ModelInfoResponse(BaseModel):
    model_name: str
    model_alias: str
    model_uri: str
    model_loaded: bool