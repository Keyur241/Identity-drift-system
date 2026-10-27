from sqlalchemy.orm import Session

from .models import AgentModel, AuditLogModel


def _s(id, name, role, desc, actions, resources, dests):
    return dict(id=id, name=name, declared_role=role, description=desc, allowed_actions=actions, allowed_resources=resources, approved_destinations=dests)


SEEDS = [
    _s("agent-procurement-alpha", "Procurement Agent Alpha", "Procurement Operations", "Supplier quotes and purchase requests (original demo agent).",
       ["read", "create", "send"], ["/db/suppliers/*", "/docs/suppliers/*", "/api/purchase-requests*"], ["erp.corp.internal", "suppliers.corp.com"]),
    _s("agent-finance", "Finance Agent", "Finance Operations", "Processes invoices, payments, expense reports and financial records. No payment approval by default.",
       ["read", "retrieve", "create"], ["/finance/invoices/*", "/finance/expenses/*", "/finance/records/authorized/*"], ["erp.corp.internal"]),
    _s("agent-hr", "HR Agent", "HR Operations", "Employee records, leave requests and onboarding. No access to confidential salary data.",
       ["read", "process_leave", "onboard"], ["/hr/employees/basic/*", "/hr/leave/*", "/hr/onboarding/*"], ["hris.corp.internal"]),
    _s("agent-support", "Customer Support Agent", "Customer Support", "Answers customer questions and retrieves order information for assigned tickets.",
       ["read", "respond"], ["/support/tickets/assigned/*", "/orders/*"], ["helpdesk.corp.internal"]),
    _s("agent-devops", "DevOps Agent", "DevOps / Infrastructure", "Monitors servers, supports deployments. No production admin or secret access by default.",
       ["read", "deploy"], ["/metrics/*", "/logs/app/*", "/deploy/authorized/*"], ["ci.corp.internal"]),
    _s("agent-procurement-ops", "Procurement Agent", "Procurement Operations", "Purchase orders, supplier info and inventory. No supplier bank changes or unlimited purchasing.",
       ["read", "create"], ["/db/suppliers/info/*", "/inventory/*", "/api/purchase-requests*"], ["erp.corp.internal"]),
]
BY_ID = {s["id"]: s for s in SEEDS}


def baseline_of(s: dict) -> dict:
    return {"role": s["declared_role"], "actions": list(s["allowed_actions"]), "resources": list(s["allowed_resources"]),
            "destinations": list(s["approved_destinations"])}


def sync_agents(db: Session):
    """Create missing agents; backfill description/baseline on agents from an older DB."""
    for s in SEEDS:
        a = db.get(AgentModel, s["id"])
        if not a:
            a = AgentModel(status="ACTIVE", baseline=baseline_of(s), risk_score=0.0, session_active=True, restricted_permissions=[], drift_sig="", **s)
            db.add(a)
            db.add(AuditLogModel(actor="system", action_taken="AGENT_REGISTERED", details=f"Seeded {s['name']}."))
        else:
            if not a.description:
                a.description = s["description"]
            if not a.baseline:
                a.baseline = {"role": a.declared_role, "actions": list(a.allowed_actions), "resources": list(a.allowed_resources), "destinations": list(a.approved_destinations)}
            if a.session_active is None:
                a.session_active = True
            if a.restricted_permissions is None:
                a.restricted_permissions = []
    db.commit()


def restore_agent(db: Session, agent: AgentModel, to_seed: bool):
    src = baseline_of(BY_ID[agent.id]) if (to_seed and agent.id in BY_ID) else (agent.baseline or baseline_of(BY_ID[agent.id]))
    agent.declared_role = src["role"]
    agent.allowed_actions, agent.allowed_resources, agent.approved_destinations = list(src["actions"]), list(src["resources"]), list(src["destinations"])
    if to_seed:
        agent.baseline = dict(src)
    agent.status, agent.session_active, agent.restricted_permissions, agent.drift_sig = "ACTIVE", True, [], ""
    db.commit()
