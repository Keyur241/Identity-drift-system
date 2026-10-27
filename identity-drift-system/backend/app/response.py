"""Simulated threat response & recovery. Nothing here touches real accounts or sessions."""
from sqlalchemy.orm import Session

from . import incidents, seed
from .drift import compute_drift, refresh_risk
from .models import AgentModel, AuditLogModel, PermissionChangeModel

ACTIONS = ("contain", "revoke_session", "restrict_permission", "restore_access", "approve_baseline")


class ResponseError(ValueError):
    pass


def recommend(agent: AgentModel) -> list[dict]:
    r = agent.risk_score or 0
    d = compute_drift(agent)
    adds = [i for k in ("actions", "resources", "destinations") for i in d["added"][k]]
    recs = []
    if r >= 75:
        recs += [{"action": "contain", "reason": f"Risk {r:.0f}/100 is CRITICAL: isolate the agent.", "urgency": "IMMEDIATE"},
                 {"action": "revoke_session", "reason": "Invalidate the (simulated) active session.", "urgency": "IMMEDIATE"}]
    elif r >= 55:
        recs.append({"action": "revoke_session", "reason": f"Risk {r:.0f}/100 is HIGH: revoke the session while investigating.", "urgency": "HIGH"})
    for p in adds[:3]:
        recs.append({"action": "restrict_permission", "permission": p, "reason": f"'{p}' is not in the approved baseline.", "urgency": "HIGH" if r >= 55 else "MEDIUM"})
    if adds and r < 75:
        recs.append({"action": "approve_baseline", "reason": "Only if an administrator confirms this change was authorised.", "urgency": "REVIEW"})
    if agent.status != "ACTIVE" or agent.session_active is False or agent.restricted_permissions:
        recs.append({"action": "restore_access", "reason": "After investigation, roll permissions back to baseline and restore access.", "urgency": "AFTER_INVESTIGATION"})
    if not recs:
        recs.append({"action": "monitor", "reason": "No drift or open alerts; continue monitoring.", "urgency": "NONE"})
    return recs


def execute(db: Session, agent: AgentModel, action: str, confirm: bool, permission: str | None = None, note: str = "", actor: str = "analyst") -> dict:
    if action not in ACTIONS:
        raise ResponseError(f"Unknown action '{action}'")
    if action == "restrict_permission" and not permission:
        raise ResponseError("'permission' is required for restrict_permission")
    desc = {"contain": f"Isolate {agent.name} (local status → CONTAINED).",
            "revoke_session": f"Mark the session of {agent.name} as revoked (local flag only).",
            "restrict_permission": f"Remove '{permission}' from {agent.name}'s current permissions.",
            "restore_access": f"Roll {agent.name} back to its approved baseline and restore access.",
            "approve_baseline": f"Accept {agent.name}'s CURRENT permissions as the new approved baseline."}[action]
    if not confirm:
        return {"status": "CONFIRMATION_REQUIRED", "action": action, "simulated": True, "message": f"{desc} Confirmation required (simulation only)."}
    if action == "contain":
        agent.status = "CONTAINED"
    elif action == "revoke_session":
        agent.session_active = False
    elif action == "restrict_permission":
        found = False
        for attr in ("allowed_actions", "allowed_resources", "approved_destinations"):
            cur = list(getattr(agent, attr) or [])
            if permission in cur:
                cur.remove(permission)
                setattr(agent, attr, cur)
                found = True
        if not found:
            raise ResponseError(f"'{permission}' is not currently granted to this agent")
        agent.restricted_permissions = [*(agent.restricted_permissions or []), permission]
        db.add(PermissionChangeModel(agent_id=agent.id, change_type="REVOKE", permission=permission, actor=actor, approved=True, detail="Restricted by response workflow (simulated)."))
    elif action == "restore_access":
        seed.restore_agent(db, agent, to_seed=False)
    elif action == "approve_baseline":
        agent.baseline = {"role": agent.declared_role, "actions": list(agent.allowed_actions), "resources": list(agent.allowed_resources),
                          "destinations": list(agent.approved_destinations)}
        agent.drift_sig = ""
        db.add(PermissionChangeModel(agent_id=agent.id, change_type="BASELINE_APPROVED", permission="*", actor=actor, approved=True, detail=note or "Admin approved current permissions."))
    db.add(AuditLogModel(actor=actor, action_taken=f"RESPONSE_{action.upper()}_SIMULATED", details=f"{desc} {note}".strip() + " [SIMULATION: no external system changed]"))
    db.commit()
    incidents.log_action(db, agent.id, action, desc + (f" ({permission})" if permission and action != "restrict_permission" else ""), actor)
    refresh_risk(db, agent)
    return {"status": "EXECUTED", "action": action, "simulated": True, "message": f"SIMULATED: {desc} No real account, token or session was changed."}
