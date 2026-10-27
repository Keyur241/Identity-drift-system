import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AgentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CONTAINED = "CONTAINED"
    SUSPENDED = "SUSPENDED"


class Sensitivity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Outcome(str, enum.Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    PENDING_REVIEW = "PENDING_REVIEW"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class AgentModel(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String)
    declared_role: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default=AgentStatus.ACTIVE.value)
    allowed_actions: Mapped[list] = mapped_column(JSON, default=list)
    allowed_resources: Mapped[list] = mapped_column(JSON, default=list)
    approved_destinations: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    description: Mapped[str | None] = mapped_column(Text, default="")
    baseline: Mapped[dict | None] = mapped_column(JSON, default=dict)
    risk_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    session_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    restricted_permissions: Mapped[list | None] = mapped_column(JSON, default=list)
    drift_sig: Mapped[str | None] = mapped_column(String, default="")

    @property
    def health(self) -> str:
        if self.status != "ACTIVE":
            return "Contained"
        r = self.risk_score or 0
        return "At Risk" if r >= 60 else "Monitoring" if r > 0 else "Healthy"


class EventModel(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    declared_role: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    resource_accessed: Mapped[str] = mapped_column(String)
    destination: Mapped[str | None] = mapped_column(String, nullable=True)
    data_sensitivity: Mapped[str] = mapped_column(String)
    outcome: Mapped[str] = mapped_column(String, default=Outcome.ALLOWED.value)
    parent_agent_id: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)


class AlertModel(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    risk_score: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default=AlertStatus.OPEN.value)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    actor: Mapped[str] = mapped_column(String)
    action_taken: Mapped[str] = mapped_column(String)
    details: Mapped[str] = mapped_column(Text)


class PermissionChangeModel(Base):
    __tablename__ = "permission_changes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    change_type: Mapped[str] = mapped_column(String)  # GRANT / REVOKE / BASELINE_APPROVED
    permission: Mapped[str] = mapped_column(String)
    actor: Mapped[str] = mapped_column(String)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[str] = mapped_column(Text, default="")


class IncidentModel(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    title: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="NEW")
    summary: Mapped[str] = mapped_column(Text, default="")
    alert_ids: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[list] = mapped_column(JSON, default=list)
    actions: Mapped[list] = mapped_column(JSON, default=list)
