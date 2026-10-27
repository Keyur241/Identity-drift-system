from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .models import AgentStatus, AlertStatus, Outcome, Sensitivity


class ORM(BaseModel):
    model_config = {"from_attributes": True}


class AgentCreate(BaseModel):
    name: str = Field(min_length=1)
    declared_role: str = Field(min_length=1)
    allowed_actions: list[str] = []
    allowed_resources: list[str] = []
    approved_destinations: list[str] = []


class AgentOut(ORM):
    id: str
    name: str
    declared_role: str
    status: AgentStatus
    allowed_actions: list[str]
    allowed_resources: list[str]
    approved_destinations: list[str]
    created_at: datetime
    description: str | None = None
    baseline: dict | None = None
    risk_score: float | None = 0.0
    session_active: bool | None = True
    restricted_permissions: list[str] | None = None
    health: str = "Healthy"


class ContainmentRequest(BaseModel):
    action: Literal["isolate", "release"]


class EventCreate(BaseModel):
    agent_id: str
    action: str
    resource_accessed: str
    destination: str | None = None
    data_sensitivity: Sensitivity = Sensitivity.LOW
    parent_agent_id: str | None = None


class EventOut(ORM):
    id: int
    timestamp: datetime
    agent_id: str
    declared_role: str
    action: str
    resource_accessed: str
    destination: str | None
    data_sensitivity: Sensitivity
    outcome: Outcome
    parent_agent_id: str | None
    risk_score: float


class AlertOut(ORM):
    id: int
    timestamp: datetime
    event_id: int
    agent_id: str
    risk_score: float
    severity: str
    evidence: list[str]
    explanation: str
    status: AlertStatus


class AlertResolve(BaseModel):
    status: Literal["RESOLVED", "FALSE_POSITIVE"] = "RESOLVED"


class AuditOut(ORM):
    id: int
    timestamp: datetime
    actor: str
    action_taken: str
    details: str


class IngestResult(BaseModel):
    event: EventOut
    alert: AlertOut | None = None


class SimulateRequest(BaseModel):
    scenario: Literal["normal", "drift", "update", "normal_procurement", "malicious_drift", "legitimate_role_update",
                      "finance_escalation", "hr_anomaly", "support_drift", "devops_credentials", "procurement_abuse", "attack_chain"]
    auto_recover: bool = False


class SimStep(BaseModel):
    message: str
    result: IngestResult | None = None


class SimulateResult(BaseModel):
    scenario: str
    agent_id: str
    steps: list[SimStep]


class RespondRequest(BaseModel):
    action: Literal["contain", "revoke_session", "restrict_permission", "restore_access", "approve_baseline"]
    confirm: bool = False
    permission: str | None = None
    note: str = ""


class IncidentUpdate(BaseModel):
    status: Literal["NEW", "INVESTIGATING", "CONFIRMED_THREAT", "FALSE_POSITIVE", "RESOLVED"] | None = None
    note: str | None = Field(default=None, max_length=2000)
    author: str = "analyst"
