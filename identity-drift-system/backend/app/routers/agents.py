import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import response
from ..database import get_db
from ..drift import compute_drift, refresh_risk
from ..explain import explain_agent
from ..models import AgentModel, AuditLogModel, IncidentModel
from ..schemas import AgentCreate, AgentOut, ContainmentRequest, RespondRequest

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _get(db, agent_id) -> AgentModel:
    agent = db.get(AgentModel, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


@router.get("", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)):
    return db.scalars(select(AgentModel).order_by(AgentModel.created_at, AgentModel.name)).all()


@router.post("", response_model=AgentOut, status_code=201)
def create_agent(body: AgentCreate, db: Session = Depends(get_db)):
    data = body.model_dump()
    agent = AgentModel(id=str(uuid.uuid4()), status="ACTIVE", baseline={"role": data["declared_role"], "actions": data["allowed_actions"],
                       "resources": data["allowed_resources"], "destinations": data["approved_destinations"]}, **data)
    db.add(agent)
    db.add(AuditLogModel(actor="admin", action_taken="AGENT_REGISTERED", details=f"Registered {agent.name} ({agent.declared_role})."))
    db.commit()
    return agent


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    return _get(db, agent_id)


@router.get("/{agent_id}/detail")
def detail(agent_id: str, db: Session = Depends(get_db)):
    agent = _get(db, agent_id)
    refresh_risk(db, agent)
    incs = db.scalars(select(IncidentModel).where(IncidentModel.agent_id == agent_id).order_by(IncidentModel.id.desc())).all()
    return {"agent": AgentOut.model_validate(agent), "drift": compute_drift(agent), "explanation": explain_agent(db, agent),
            "incidents": [{"id": i.id, "title": i.title, "status": i.status, "severity": i.severity, "risk_score": i.risk_score,
                           "updated_at": i.updated_at} for i in incs]}


@router.post("/{agent_id}/respond")
def respond(agent_id: str, body: RespondRequest, db: Session = Depends(get_db)):
    agent = _get(db, agent_id)
    try:
        return response.execute(db, agent, body.action, body.confirm, body.permission, body.note)
    except response.ResponseError as e:
        raise HTTPException(400, str(e))


@router.post("/{agent_id}/containment", response_model=AgentOut)
def containment(agent_id: str, body: ContainmentRequest, db: Session = Depends(get_db)):
    agent = _get(db, agent_id)
    agent.status = "CONTAINED" if body.action == "isolate" else "ACTIVE"
    db.add(AuditLogModel(actor="admin", action_taken="MANUAL_ISOLATE" if body.action == "isolate" else "MANUAL_RELEASE",
                         details=f"Manual {body.action} of {agent.name} ({agent.id}) [SIMULATION]."))
    db.commit()
    return agent
