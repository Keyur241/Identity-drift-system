"""Rule-based drift detection, risk scoring, explanation and automated containment."""
import fnmatch

from sqlalchemy.orm import Session

from . import incidents
from .config import settings
from .drift import refresh_risk, severity_for
from .models import (AgentModel, AgentStatus, AlertModel, AuditLogModel, EventModel, Outcome, Sensitivity)

SENSITIVITY_WEIGHT = {"LOW": 10, "MEDIUM": 30, "HIGH": 60, "CRITICAL": 90}
ROLE_MISMATCH_PENALTY = 20
BAD_DESTINATION_PENALTY = 30


def _match(value: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(value, p) for p in patterns)


class DetectionEngine:
    def __init__(self, block_threshold: float | None = None, review_threshold: float | None = None):
        self.block_threshold = block_threshold or settings.containment_threshold
        self.review_threshold = review_threshold or settings.review_threshold

    def score(self, agent: AgentModel, action: str, resource: str, destination: str | None, sensitivity: str):
        evidence: list[str] = []
        b = agent.baseline or {}  # expected identity; falls back to current permissions if no baseline
        actions = b.get("actions") or agent.allowed_actions
        resources = b.get("resources") or agent.allowed_resources
        dests = b.get("destinations", agent.approved_destinations)
        res_ok = _match(resource, resources)
        act_ok = action in actions
        mismatch = not (res_ok and act_ok)
        if not res_ok:
            evidence.append(f"Resource '{resource}' is outside the expected resource scope of role '{agent.declared_role}'.")
        if not act_ok:
            evidence.append(f"Action '{action}' is not in the expected actions of role '{agent.declared_role}'.")
        if mismatch and _match(resource, agent.allowed_resources) and action in agent.allowed_actions:
            evidence.append("Current credentials permit this, but it was never approved in the baseline (unapproved privilege escalation).")
        bad_dest = bool(destination) and not _match(destination, dests or [])
        if bad_dest:
            evidence.append(f"Destination '{destination}' is not an approved destination (possible exfiltration).")
        if not mismatch and not bad_dest:
            return 0.0, evidence, mismatch, bad_dest
        score = SENSITIVITY_WEIGHT[sensitivity]
        evidence.append(f"Data sensitivity {sensitivity}: base weight {score}.")
        if mismatch:
            score += ROLE_MISMATCH_PENALTY
            evidence.append(f"Role mismatch penalty +{ROLE_MISMATCH_PENALTY}.")
        if bad_dest:
            score += BAD_DESTINATION_PENALTY
            evidence.append(f"Unapproved destination penalty +{BAD_DESTINATION_PENALTY}.")
        return float(min(100, score)), evidence, mismatch, bad_dest

    def narrative(self, agent, ev, score, mismatch, bad_dest, outcome) -> str:
        text = (f"{severity_for(score).title()} Risk ({score:.0f}/100): Agent '{agent.name}' (Role: {agent.declared_role}) "
                f"attempted {'unauthorized ' if mismatch else ''}{ev.action} access on "
                f"{'restricted ' if mismatch else ''}resource '{ev.resource_accessed}' with {ev.data_sensitivity} data sensitivity")
        if bad_dest:
            text += f", coupled with an unapproved data exfiltration attempt to external host '{ev.destination}'"
        text += f". Outcome: {outcome}."
        return text

    def ingest(self, db: Session, agent: AgentModel, ev: EventModel):
        """Evaluate, persist event, create alert, apply containment, write audit log."""
        sens = ev.data_sensitivity.value if isinstance(ev.data_sensitivity, Sensitivity) else ev.data_sensitivity
        ev.data_sensitivity = sens
        ev.declared_role = agent.declared_role
        score, evidence, mismatch, bad_dest = self.score(agent, ev.action, ev.resource_accessed, ev.destination, sens)
        ev.risk_score = score
        if score >= self.block_threshold:
            ev.outcome = Outcome.BLOCKED.value
        elif score >= self.review_threshold or (score == 0 and (agent.status != AgentStatus.ACTIVE.value or agent.session_active is False)):
            ev.outcome = Outcome.PENDING_REVIEW.value  # contained agents: even clean work waits for review
        else:
            ev.outcome = Outcome.ALLOWED.value
        db.add(ev)
        db.flush()
        alert = None
        if score > 0:
            alert = AlertModel(event_id=ev.id, agent_id=agent.id, risk_score=score, severity=severity_for(score),
                               evidence=evidence, explanation=self.narrative(agent, ev, score, mismatch, bad_dest, ev.outcome),
                               status="OPEN")
            db.add(alert)
        if ev.outcome == Outcome.BLOCKED.value:
            db.add(AuditLogModel(actor="detection-engine", action_taken="EVENT_BLOCKED",
                                 details=f"Event #{ev.id} ({ev.action} {ev.resource_accessed}) blocked, risk {score:.0f}."))
            if agent.status != AgentStatus.CONTAINED.value:
                agent.status = AgentStatus.CONTAINED.value
                db.add(AuditLogModel(actor="detection-engine", action_taken="AGENT_CONTAINED",
                                     details=f"Agent '{agent.name}' ({agent.id}) auto-contained after event #{ev.id}."))
        db.commit()
        db.refresh(ev)
        if alert:
            db.refresh(alert)
            incidents.attach(db, agent, alert)
        refresh_risk(db, agent)
        return ev, alert


engine = DetectionEngine()
