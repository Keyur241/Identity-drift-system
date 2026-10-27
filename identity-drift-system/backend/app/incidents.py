from sqlalchemy import select
from sqlalchemy.orm import Session

from .drift import refresh_risk, severity_for
from .models import AgentModel, AlertModel, AuditLogModel, IncidentModel, utcnow

ACTIVE = ("NEW", "INVESTIGATING", "CONFIRMED_THREAT")
STATUSES = ("NEW", "INVESTIGATING", "CONFIRMED_THREAT", "FALSE_POSITIVE", "RESOLVED")


def active_incident(db: Session, agent_id: str):
    return db.scalars(select(IncidentModel).where(IncidentModel.agent_id == agent_id, IncidentModel.status.in_(ACTIVE))
                      .order_by(IncidentModel.id.desc())).first()


def attach(db: Session, agent: AgentModel, alert: AlertModel) -> IncidentModel:
    inc = active_incident(db, agent.id)
    if inc:
        inc.alert_ids = [*inc.alert_ids, alert.id]
        inc.risk_score = max(inc.risk_score, alert.risk_score)
        inc.severity = severity_for(inc.risk_score)
        inc.updated_at = utcnow()
        inc.summary = f"{len(inc.alert_ids)} alerts on {agent.name}; highest risk {inc.risk_score:.0f}/100. Latest: {alert.explanation}"
    else:
        inc = IncidentModel(agent_id=agent.id, title=f"Identity drift: {agent.name}", severity=alert.severity, risk_score=alert.risk_score,
                            status="NEW", summary=f"1 alert on {agent.name}; risk {alert.risk_score:.0f}/100. {alert.explanation}",
                            alert_ids=[alert.id], notes=[], actions=[])
        db.add(inc)
        db.add(AuditLogModel(actor="detection-engine", action_taken="INCIDENT_OPENED", details=f"Incident opened for {agent.name} ({agent.id})."))
    db.commit()
    return inc


def log_action(db: Session, agent_id: str, action: str, detail: str, actor: str):
    inc = active_incident(db, agent_id)
    if inc:
        inc.actions = [*inc.actions, {"ts": utcnow().isoformat(), "actor": actor, "action": action, "detail": detail, "simulated": True}]
        inc.updated_at = utcnow()
        db.commit()


def add_note(db: Session, inc: IncidentModel, author: str, text: str):
    inc.notes = [*inc.notes, {"ts": utcnow().isoformat(), "author": author, "text": text}]
    inc.updated_at = utcnow()
    db.commit()


def set_status(db: Session, inc: IncidentModel, status: str, author: str = "analyst", note: str | None = None):
    old = inc.status
    inc.status = status
    add_note(db, inc, author, f"Status changed {old} → {status}." + (f" {note}" if note else ""))
    db.add(AuditLogModel(actor=author, action_taken=f"INCIDENT_{status}", details=f"Incident #{inc.id} {old} → {status}."))
    if status in ("RESOLVED", "FALSE_POSITIVE"):
        for a in db.scalars(select(AlertModel).where(AlertModel.id.in_(inc.alert_ids))):
            a.status = status
    db.commit()
    agent = db.get(AgentModel, inc.agent_id)
    if agent:
        refresh_risk(db, agent)
