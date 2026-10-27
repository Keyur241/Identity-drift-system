from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..drift import refresh_risk
from ..models import AgentModel, AlertModel, AuditLogModel
from ..schemas import AlertOut, AlertResolve, AuditOut

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(status: str | None = None, db: Session = Depends(get_db)):
    q = select(AlertModel).order_by(AlertModel.id.desc()).limit(200)
    if status:
        q = q.where(AlertModel.status == status)
    return db.scalars(q).all()


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve(alert_id: int, body: AlertResolve = AlertResolve(), db: Session = Depends(get_db)):
    alert = db.get(AlertModel, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = body.status
    db.add(AuditLogModel(actor="analyst", action_taken=f"ALERT_{body.status}", details=f"Alert #{alert.id} marked {body.status}."))
    db.commit()
    agent = db.get(AgentModel, alert.agent_id)
    if agent:
        refresh_risk(db, agent)
    return alert


@router.get("/audit", response_model=list[AuditOut])
def audit(limit: int = 100, db: Session = Depends(get_db)):
    return db.scalars(select(AuditLogModel).order_by(AuditLogModel.id.desc()).limit(min(limit, 500))).all()
