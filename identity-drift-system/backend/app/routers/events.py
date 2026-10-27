from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..engine import engine
from ..models import AgentModel, EventModel
from ..schemas import AlertOut, EventCreate, EventOut, IngestResult, SimulateRequest, SimulateResult
from ..simulator import reset_all, run_scenario

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(limit: int = 100, agent_id: str | None = None, db: Session = Depends(get_db)):
    q = select(EventModel).order_by(EventModel.id.desc()).limit(min(limit, 500))
    if agent_id:
        q = q.where(EventModel.agent_id == agent_id)
    return db.scalars(q).all()


@router.post("", response_model=IngestResult, status_code=201)
def log_event(body: EventCreate, db: Session = Depends(get_db)):
    agent = db.get(AgentModel, body.agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    ev, alert = engine.ingest(db, agent, EventModel(**body.model_dump()))
    return IngestResult(event=EventOut.model_validate(ev), alert=AlertOut.model_validate(alert) if alert else None)


@router.post("/simulate", response_model=SimulateResult)
def simulate(body: SimulateRequest, db: Session = Depends(get_db)):
    return run_scenario(db, body.scenario, body.auto_recover)


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    reset_all(db)
    return {"status": "reset"}
