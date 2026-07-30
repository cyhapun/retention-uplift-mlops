from datetime import datetime

from pydantic import BaseModel, Field


class PolicyAction(BaseModel):
    cost: float = Field(ge=0)
    min_expected_value: float = Field(ge=0)
    min_uplift: float = Field(ge=0, le=1)
    priority: int = Field(ge=0)


class PolicyDocument(BaseModel):
    actions: dict[str, PolicyAction]
    min_uplift_for_action: float = Field(ge=0, le=1)
    max_daily_budget: float = Field(ge=0)


class PolicySnapshot(BaseModel):
    version_id: str
    version_number: int
    created_at: datetime | None = None
    activated_at: datetime | None = None
    created_by: str
    is_active: bool = False
    editable: bool
    policy: PolicyDocument


class PolicyValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    policy: PolicyDocument


class PolicyActivationRequest(BaseModel):
    policy: PolicyDocument
    expected_version_id: str | None = None
    confirm: bool = False
    change_summary: str = Field(default="", max_length=500)


class PolicyPreviewRequest(BaseModel):
    policy: PolicyDocument
    limit: int = Field(default=1000, ge=1, le=5000)


class PolicyRollbackRequest(BaseModel):
    expected_version_id: str | None = None
    confirm: bool = False


class PolicyVersionDeleteRequest(BaseModel):
    expected_version_id: str | None = None
    confirm: bool = False


class PolicyPreviewResponse(BaseModel):
    available: bool
    reason: str | None = None
    population: int = 0
    evaluation_period: str | None = None
    changed_decisions: int = 0
    estimated_action_distribution: dict[str, int] = Field(default_factory=dict)
    estimated_average_expected_value: float | None = None


class PolicyAuditResponse(BaseModel):
    audit_id: str
    action: str
    actor: str
    status: str
    outcome: str
    source_version_id: str | None = None
    target_version_id: str | None = None
    created_at: datetime | None = None
