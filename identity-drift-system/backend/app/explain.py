"""Deterministic, evidence-grounded risk explanation. No LLM is called; nothing is invented beyond stored events/permissions."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .drift import compute_drift, severity_for
from .models import AgentModel, AlertModel, EventModel
from .response import recommend


def explain_agent(db: Session, agent: AgentModel, alert_ids: list[int] | None = None) -> dict:
    d = compute_drift(agent)
    alerts = [a for a in db.scalars(select(AlertModel).where(AlertModel.agent_id == agent.id, AlertModel.status == "OPEN").order_by(AlertModel.id))
              if alert_ids is None or a.id in alert_ids]
    factors = [{"source": "permission_drift", "severity": f["severity"], "points": f["points"], "event_id": None, "description": f["description"]}
               for f in d["factors"]]
    n_ev = 0
    for a in alerts:
        ev = db.get(EventModel, a.event_id)
        if not ev or ev.action == "permission_change":
            continue
        n_ev += 1
        dest = f" → {ev.destination}" if ev.destination else ""
        factors.append({"source": "event", "severity": a.severity, "points": a.risk_score, "event_id": ev.id, "alert_id": a.id,
                        "description": f"Event #{ev.id}: {ev.action} on {ev.resource_accessed}{dest} ({ev.data_sensitivity}, {ev.outcome}). " + " ".join(a.evidence[:3])})
    score = agent.risk_score or 0
    parts = [f"{agent.name} ({agent.declared_role}) is {agent.health} with risk {score:.0f}/100 ({severity_for(score) if score else 'no risk'})."]
    if d["factors"]:
        parts.append(f"{len(d['factors'])} permission(s) differ from the approved baseline: {', '.join(f['item'] for f in d['factors'])}.")
    if n_ev:
        parts.append(f"{n_ev} open alert(s) come from specific agent events outside the expected role.")
    if not d["factors"] and not n_ev:
        parts.append("No drift or open alerts were found in stored data.")
    return {"agent_id": agent.id, "risk_score": score, "severity": severity_for(score) if score else "NONE", "summary": " ".join(parts),
            "factors": sorted(factors, key=lambda f: -f["points"]), "recommendations": recommend(agent),
            "method": "rule-based (deterministic)", "llm_used": False}
