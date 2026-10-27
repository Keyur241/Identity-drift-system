"""Identity drift comparison (baseline vs current), drift alerts and independent per-agent risk."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AgentModel, AlertModel, AuditLogModel, EventModel

PRIV_ACTIONS = {"approve_payment", "approve_purchase", "hr_admin", "prod_admin", "admin", "modify_supplier_bank", "read_secrets", "modify_records"}
SENSITIVE = ("/secrets", "/prod", "/finance/payments", "/hr/employees/confidential", "/hr/employees/*", "/db/suppliers/bank",
             "/admin", "purchase-approvals", "/db/customers")


def severity_for(score: float) -> str:
    return "CRITICAL" if score >= 75 else "HIGH" if score >= 55 else "MEDIUM" if score >= 25 else "LOW"


def _pts_sev(p: int) -> str:
    return "HIGH" if p >= 40 else "MEDIUM" if p >= 25 else "LOW"


def compute_drift(agent: AgentModel) -> dict:
    b = agent.baseline or {}
    cur = {"actions": list(agent.allowed_actions or []), "resources": list(agent.allowed_resources or []),
           "destinations": list(agent.approved_destinations or [])}
    exp = {k: list(b.get(k, cur[k])) for k in cur}
    added = {k: [x for x in cur[k] if x not in exp[k]] for k in cur}
    removed = {k: [x for x in exp[k] if x not in cur[k]] for k in cur}
    f = []

    def add(kind, item, p, text):
        f.append({"kind": kind, "item": item, "points": p, "severity": _pts_sev(p), "description": text})

    for a in added["actions"]:
        priv = a in PRIV_ACTIONS
        add("NEW_ACTION", a, 40 if priv else 15, f"Action '{a}' is granted but not in the approved baseline" + (" (privileged action: possible privilege escalation)." if priv else "."))
    for r in added["resources"]:
        sens = any(s in r for s in SENSITIVE)
        add("NEW_RESOURCE", r, 30 if sens else 10, f"Resource scope '{r}' is granted but not in the approved baseline" + (" (sensitive resource)." if sens else "."))
    for d in added["destinations"]:
        add("NEW_DESTINATION", d, 25, f"Destination '{d}' was added to approved destinations without baseline approval.")
    role_exp = b.get("role", agent.declared_role)
    if agent.declared_role != role_exp:
        add("ROLE_CHANGE", agent.declared_role, 20, f"Declared role changed from '{role_exp}' to '{agent.declared_role}'.")
    score = float(min(100, sum(x["points"] for x in f)))
    return {"role_expected": role_exp, "role_actual": agent.declared_role, "expected": exp, "actual": cur, "added": added,
            "removed": removed, "factors": f, "score": score, "severity": severity_for(score) if score else "NONE"}


def evaluate_drift(db: Session, agent: AgentModel):
    """Create a drift event + alert when un-baselined permissions appear. Returns (event, alert) or None."""
    from . import incidents  # local import avoids a cycle
    d = compute_drift(agent)
    if d["score"] == 0:
        if agent.drift_sig:
            agent.drift_sig = ""
            db.commit()
        refresh_risk(db, agent)
        return None
    sig = "|".join(sorted(f"{x['kind']}:{x['item']}" for x in d["factors"]))
    if sig == agent.drift_sig:
        return None
    items = [x["item"] for x in d["factors"]]
    sens = "CRITICAL" if d["score"] >= 70 else "HIGH" if d["score"] >= 40 else "MEDIUM"
    ev = EventModel(agent_id=agent.id, declared_role=agent.declared_role, action="permission_change",
                    resource_accessed="; ".join(items), data_sensitivity=sens, outcome="PENDING_REVIEW", risk_score=d["score"])
    db.add(ev)
    db.flush()
    expl = (f"{severity_for(d['score']).title()} Risk ({d['score']:.0f}/100): Agent '{agent.name}' (Role: {agent.declared_role}) now holds "
            f"permissions that are not in its approved baseline: {', '.join(items)}. This may be privilege escalation; no approved role update covers it.")
    alert = AlertModel(event_id=ev.id, agent_id=agent.id, risk_score=d["score"], severity=severity_for(d["score"]),
                       evidence=[x["description"] for x in d["factors"]], explanation=expl, status="OPEN")
    db.add(alert)
    db.add(AuditLogModel(actor="detection-engine", action_taken="DRIFT_DETECTED", details=f"{agent.name} ({agent.id}) drift score {d['score']:.0f}: {', '.join(items)}."))
    agent.drift_sig = sig
    db.commit()
    db.refresh(ev)
    db.refresh(alert)
    incidents.attach(db, agent, alert)
    refresh_risk(db, agent)
    return ev, alert


def refresh_risk(db: Session, agent: AgentModel) -> float:
    open_ = db.scalars(select(AlertModel).where(AlertModel.agent_id == agent.id, AlertModel.status == "OPEN")).all()
    base = max([a.risk_score for a in open_], default=0.0)
    extra = min(15, 5 * (len(open_) - 1)) if len(open_) > 1 else 0
    agent.risk_score = float(min(100, max(base, compute_drift(agent)["score"]) + extra))
    db.commit()
    return agent.risk_score
