import csv
import io
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import incidents as inc_svc
from ..chains import detect_chains
from ..database import get_db
from ..explain import explain_agent
from ..models import AgentModel, AlertModel, AuditLogModel, EventModel, IncidentModel, PermissionChangeModel
from ..schemas import IncidentUpdate

router = APIRouter(prefix="/api", tags=["incidents"])


def _row(i: IncidentModel, agents) -> dict:
    return {"id": i.id, "agent_id": i.agent_id, "agent_name": agents.get(i.agent_id, i.agent_id), "title": i.title, "severity": i.severity,
            "risk_score": i.risk_score, "status": i.status, "created_at": i.created_at, "updated_at": i.updated_at, "alert_count": len(i.alert_ids)}


def _timeline(db: Session, i: IncidentModel, agent: AgentModel) -> list[dict]:
    since = i.created_at - timedelta(minutes=10)
    items = []
    for e in db.scalars(select(EventModel).where(EventModel.agent_id == i.agent_id, EventModel.timestamp >= since)):
        items.append({"ts": e.timestamp, "type": "EVENT", "text": f"{e.action} {e.resource_accessed}" + (f" → {e.destination}" if e.destination else "") + f" [{e.data_sensitivity}] risk {e.risk_score:.0f} → {e.outcome}"})
    for p in db.scalars(select(PermissionChangeModel).where(PermissionChangeModel.agent_id == i.agent_id, PermissionChangeModel.timestamp >= since)):
        items.append({"ts": p.timestamp, "type": "PERMISSION_CHANGE", "text": f"{p.change_type} '{p.permission}' by {p.actor} ({'approved' if p.approved else 'NOT approved'})"})
    for a in db.scalars(select(AuditLogModel).where(AuditLogModel.timestamp >= since)):
        if agent.id in a.details or agent.name in a.details:
            items.append({"ts": a.timestamp, "type": "AUDIT", "text": f"{a.actor}: {a.action_taken} — {a.details}"})
    for n in i.notes:
        items.append({"ts": datetime.fromisoformat(n["ts"]), "type": "NOTE", "text": f"{n['author']}: {n['text']}"})
    return sorted(items, key=lambda x: x["ts"])


def _full(db: Session, i: IncidentModel) -> dict:
    agent = db.get(AgentModel, i.agent_id)
    alerts = db.scalars(select(AlertModel).where(AlertModel.id.in_(i.alert_ids))).all()
    chains = [c["id"] for c in detect_chains(db) if i.id in c["incident_ids"]]
    return {**_row(i, {agent.id: agent.name}), "summary": i.summary, "notes": i.notes, "actions": i.actions, "chain_ids": chains,
            "alerts": [{"id": a.id, "event_id": a.event_id, "risk_score": a.risk_score, "severity": a.severity, "status": a.status,
                        "evidence": a.evidence, "explanation": a.explanation} for a in alerts],
            "timeline": _timeline(db, i, agent), "explanation": explain_agent(db, agent, alert_ids=i.alert_ids or None)}


def _get(db, iid) -> IncidentModel:
    i = db.get(IncidentModel, iid)
    if not i:
        raise HTTPException(404, "Incident not found")
    return i


@router.get("/incidents")
def list_incidents(severity: str | None = None, agent_id: str | None = None, status: str | None = None,
                   date_from: str | None = Query(None, description="YYYY-MM-DD"), date_to: str | None = None, db: Session = Depends(get_db)):
    q = select(IncidentModel).order_by(IncidentModel.id.desc())
    try:
        if severity: q = q.where(IncidentModel.severity == severity)
        if agent_id: q = q.where(IncidentModel.agent_id == agent_id)
        if status: q = q.where(IncidentModel.status == status)
        if date_from: q = q.where(IncidentModel.created_at >= datetime.fromisoformat(date_from))
        if date_to: q = q.where(IncidentModel.created_at < datetime.fromisoformat(date_to) + timedelta(days=1))
    except ValueError:
        raise HTTPException(400, "Dates must be YYYY-MM-DD")
    agents = {a.id: a.name for a in db.scalars(select(AgentModel))}
    return [_row(i, agents) for i in db.scalars(q)]


@router.get("/incidents/{iid}")
def get_incident(iid: int, db: Session = Depends(get_db)):
    return _full(db, _get(db, iid))


@router.patch("/incidents/{iid}")
def update_incident(iid: int, body: IncidentUpdate, db: Session = Depends(get_db)):
    i = _get(db, iid)
    if body.status is None and not (body.note and body.note.strip()):
        raise HTTPException(400, "Provide a status and/or a note")
    if body.status and body.status != i.status:
        inc_svc.set_status(db, i, body.status, body.author, body.note.strip() if body.note else None)
    elif body.note and body.note.strip():
        inc_svc.add_note(db, i, body.author, body.note.strip())
    return _full(db, i)


@router.get("/incidents/{iid}/report")
def report(iid: int, format: Literal["json", "csv"] = "json", db: Session = Depends(get_db)):
    full = _full(db, _get(db, iid))
    full["generated_at"] = datetime.utcnow().isoformat() + "Z"
    full["mode"] = "SIMULATION: no real external systems were modified"
    if format == "json":
        import json
        from fastapi.encoders import jsonable_encoder
        return Response(json.dumps(jsonable_encoder(full), indent=2), media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="incident-{iid}.json"'})
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["incident_id", "agent_id", "agent_name", "risk_score", "severity", "status", "evidence", "remediation_actions", "timestamp", "item_type", "item_detail"]
    w.writerow(cols)
    ev = " | ".join(e for a in full["alerts"] for e in a["evidence"])
    rem = " | ".join(f"{a['ts']} {a['action']}: {a['detail']}" for a in full["actions"])
    base = [iid, full["agent_id"], full["agent_name"], full["risk_score"], full["severity"], full["status"], ev, rem]
    for t in full["timeline"] or [{"ts": "", "type": "", "text": ""}]:
        w.writerow([*base, t["ts"].isoformat() if hasattr(t["ts"], "isoformat") else t["ts"], t["type"], t["text"]])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="incident-{iid}.csv"'})


@router.get("/chains")
def chains(db: Session = Depends(get_db)):
    return detect_chains(db)
