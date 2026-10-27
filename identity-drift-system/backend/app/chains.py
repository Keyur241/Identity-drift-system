"""Multi-agent attack chain correlation. Chains are always 'SUSPECTED' and require explicit linking evidence."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .drift import severity_for
from .models import AgentModel, AlertModel, EventModel, IncidentModel

WINDOW_SECONDS = 30 * 60


def detect_chains(db: Session) -> list[dict]:
    events = db.scalars(select(EventModel).order_by(EventModel.id)).all()
    agents = {a.id: a for a in db.scalars(select(AgentModel))}
    uf = {}

    def find(x):
        uf.setdefault(x, x)
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = uf[x]
        return x

    links = []
    for b in events:
        if b.risk_score <= 0 or b.action == "permission_change":
            continue
        done = set()  # link each earlier agent only via its most recent qualifying event
        for a in reversed(events):
            if a.id >= b.id or a.agent_id == b.agent_id or a.action == "permission_change" or a.agent_id in done:
                continue
            if (b.timestamp - a.timestamp).total_seconds() > WINDOW_SECONDS:
                continue
            if not (a.risk_score > 0 or a.data_sensitivity in ("HIGH", "CRITICAL")):
                continue
            why = []
            if b.parent_agent_id == a.agent_id:
                why.append(f"{agents[b.agent_id].name} acted on delegation from {agents[a.agent_id].name}")
            if a.resource_accessed == b.resource_accessed:
                why.append(f"both touched '{a.resource_accessed}'")
            if why:
                done.add(a.agent_id)
                links.append({"from_event": a.id, "to_event": b.id, "from_agent": a.agent_id, "to_agent": b.agent_id, "reasons": why})
                uf[find(a.id)] = find(b.id)
    groups: dict[int, set] = {}
    for l in links:
        for e in (l["from_event"], l["to_event"]):
            groups.setdefault(find(e), set()).add(e)
    by_id = {e.id: e for e in events}
    alert_by_ev = {a.event_id: a for a in db.scalars(select(AlertModel))}
    out = []
    for ids in groups.values():
        evs = sorted((by_id[i] for i in ids), key=lambda e: e.id)
        aids = []
        for e in evs:
            if e.agent_id not in aids:
                aids.append(e.agent_id)
        if len(aids) < 2:
            continue
        mx = max(e.risk_score for e in evs)
        chain_links = [l for l in links if l["from_event"] in ids and l["to_event"] in ids]
        alert_ids = {alert_by_ev[e.id].id for e in evs if e.id in alert_by_ev}
        incs = [i.id for i in db.scalars(select(IncidentModel)) if alert_ids & set(i.alert_ids)]
        out.append({
            "id": f"chain-{evs[0].id}", "status": "SUSPECTED", "severity": severity_for(mx), "max_risk": mx,
            "entry_point": {"agent_id": aids[0], "agent_name": agents[aids[0]].name, "event_id": evs[0].id},
            "agents": [{"id": i, "name": agents[i].name, "role": agents[i].declared_role, "risk": agents[i].risk_score or 0} for i in aids],
            "resources": sorted({e.resource_accessed for e in evs}),
            "steps": [{"n": n + 1, "event_id": e.id, "timestamp": e.timestamp, "agent_id": e.agent_id, "agent_name": agents[e.agent_id].name,
                       "action": e.action, "resource": e.resource_accessed, "destination": e.destination, "sensitivity": e.data_sensitivity,
                       "outcome": e.outcome, "risk": e.risk_score, "parent_agent_id": e.parent_agent_id} for n, e in enumerate(evs)],
            "links": chain_links,
            "evidence": [f"Event #{l['from_event']} ({agents[l['from_agent']].name}) → event #{l['to_event']} ({agents[l['to_agent']].name}): " + "; ".join(l["reasons"]) + "." for l in chain_links],
            "incident_ids": incs,
            "note": "Suspected chain based on delegation / shared-resource links within 30 minutes; not a confirmed attack until an analyst confirms the incident.",
        })
    return sorted(out, key=lambda c: -c["steps"][-1]["event_id"])
