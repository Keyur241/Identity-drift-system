"""Scenario runner. Every event goes through the real DetectionEngine / drift evaluator."""
from sqlalchemy.orm import Session

from . import incidents, response, seed
from .drift import evaluate_drift
from .engine import engine
from .models import AgentModel, AuditLogModel, EventModel, PermissionChangeModel
from .schemas import AlertOut, EventOut, IngestResult, SimStep, SimulateResult

DEMO_AGENT_ID = "agent-procurement-alpha"
ALIASES = {"normal_procurement": "normal", "malicious_drift": "drift", "legitimate_role_update": "update"}
FIN, HR, SUP, DEV, PRO = "agent-finance", "agent-hr", "agent-support", "agent-devops", "agent-procurement-ops"


def ensure_demo_agent(db: Session) -> AgentModel:
    seed.sync_agents(db)
    return db.get(AgentModel, DEMO_AGENT_ID)


def _step(msg, ev, alert):
    return SimStep(message=msg, result=IngestResult(event=EventOut.model_validate(ev), alert=AlertOut.model_validate(alert) if alert else None))


def _ev(db, aid, msg, **kw) -> SimStep:
    ev, alert = engine.ingest(db, db.get(AgentModel, aid), EventModel(agent_id=aid, **kw))
    return _step(msg, ev, alert)


def _grant(db, aid, msg, actions=(), resources=()) -> SimStep:
    agent = db.get(AgentModel, aid)
    agent.allowed_actions = [*agent.allowed_actions, *[a for a in actions if a not in agent.allowed_actions]]
    agent.allowed_resources = [*agent.allowed_resources, *[r for r in resources if r not in agent.allowed_resources]]
    for p in [*actions, *resources]:
        db.add(PermissionChangeModel(agent_id=aid, change_type="GRANT", permission=p, actor="unknown-process", approved=False, detail=msg))
    db.add(AuditLogModel(actor="unknown-process", action_taken="PERMISSION_GRANTED",
                         details=f"{agent.name} ({aid}) granted {', '.join([*actions, *resources])} with no approval record."))
    db.commit()
    r = evaluate_drift(db, agent)
    return _step(msg, r[0], r[1]) if r else SimStep(message=msg)


def _prep(db, *aids):
    for aid in aids:
        a = db.get(AgentModel, aid)
        seed.restore_agent(db, a, to_seed=True)
        db.add(AuditLogModel(actor="simulator", action_taken="SCENARIO_PREP", details=f"{a.name} restored to seed baseline for a repeatable run."))
    db.commit()


def _auto_recover(db, aids, steps):
    for aid in aids:
        agent = db.get(AgentModel, aid)
        inc = incidents.active_incident(db, aid)
        if not inc:
            continue
        incidents.set_status(db, inc, "INVESTIGATING", "analyst", "Simulated analyst review started.")
        incidents.set_status(db, inc, "CONFIRMED_THREAT", "analyst", "Evidence reviewed: permissions/events outside baseline.")
        r = response.execute(db, agent, "restore_access", True, note="Post-investigation recovery.")
        incidents.set_status(db, inc, "RESOLVED", "analyst", "Access restored to baseline.")
        steps.append(SimStep(message=f"Recovery: incident #{inc.id} investigated, confirmed, and resolved. {r['message']}"))


def run_scenario(db: Session, name: str, auto_recover: bool = False) -> SimulateResult:
    name = ALIASES.get(name, name)
    seed.sync_agents(db)
    S: list[SimStep] = []
    A = DEMO_AGENT_ID
    touched = [A]
    if name == "normal":
        _prep(db, A)
        S += [_ev(db, A, "Agent reads supplier price list.", action="read", resource_accessed="/db/suppliers/prices", data_sensitivity="LOW"),
              _ev(db, A, "Agent creates a purchase request.", action="create", resource_accessed="/api/purchase-requests/PR-1042", data_sensitivity="MEDIUM")]
    elif name == "drift":
        _prep(db, A)
        S += [_ev(db, A, "Agent reads supplier PDF containing hidden injected instructions.", action="read", resource_accessed="/docs/suppliers/quote_injected.pdf", data_sensitivity="MEDIUM"),
              _ev(db, A, "Injected prompt makes agent read HR salary table.", action="read", resource_accessed="/db/hr/salaries", data_sensitivity="CRITICAL"),
              _ev(db, A, "Agent attempts to send salary data to an unknown external host.", action="send", resource_accessed="/db/hr/salaries", destination="api.external-leak.com", data_sensitivity="CRITICAL"),
              _ev(db, A, "Safe follow-up work while contained: supplier price lookup.", action="read", resource_accessed="/db/suppliers/prices", data_sensitivity="LOW")]
    elif name == "update":
        _prep(db, A)
        agent = db.get(AgentModel, A)
        agent.allowed_actions = [*agent.allowed_actions, "read"] if "read" not in agent.allowed_actions else agent.allowed_actions
        agent.allowed_resources = [*agent.allowed_resources, "/db/finance/budgets/*"]
        agent.baseline = {"role": agent.declared_role, "actions": list(agent.allowed_actions), "resources": list(agent.allowed_resources), "destinations": list(agent.approved_destinations)}
        db.add(PermissionChangeModel(agent_id=A, change_type="GRANT", permission="/db/finance/budgets/*", actor="admin", approved=True, detail="Approved budget-review responsibility."))
        db.add(AuditLogModel(actor="admin", action_taken="ROLE_PROFILE_UPDATED", details=f"Admin approved new responsibility: read /db/finance/budgets/* for {agent.name}; baseline updated."))
        db.commit()
        S.append(SimStep(message="Admin approves budget-review responsibility; permissions AND baseline updated."))
        S += [_ev(db, A, f"Agent performs newly approved budget read #{i}.", action="read", resource_accessed=f"/db/finance/budgets/q{i}", data_sensitivity="HIGH") for i in (1, 2)]
    elif name == "finance_escalation":
        touched = [FIN]; _prep(db, FIN)
        S += [_ev(db, FIN, "Finance Agent reads an invoice (normal).", action="read", resource_accessed="/finance/invoices/INV-2201", data_sensitivity="LOW"),
              _grant(db, FIN, "Finance Agent unexpectedly receives payment-approval privileges.", ["approve_payment"], ["/finance/payments/*"]),
              _ev(db, FIN, "Agent uses the new privilege to approve a payment batch.", action="approve_payment", resource_accessed="/finance/payments/batch-4471", data_sensitivity="CRITICAL"),
              _ev(db, FIN, "Agent attempts to modify the general ledger outside its scope.", action="modify_records", resource_accessed="/finance/records/ledger", data_sensitivity="HIGH")]
    elif name == "hr_anomaly":
        touched = [HR]; _prep(db, HR)
        S += [_ev(db, HR, "HR Agent reads a basic employee profile (normal).", action="read", resource_accessed="/hr/employees/basic/E102", data_sensitivity="LOW"),
              _ev(db, HR, "HR Agent attempts to read confidential salary records.", action="read", resource_accessed="/hr/employees/confidential/salaries", data_sensitivity="CRITICAL"),
              _grant(db, HR, "HR Agent receives elevated HR administrator permissions.", ["hr_admin"], ["/hr/employees/*"])]
    elif name == "support_drift":
        touched = [SUP]; _prep(db, SUP)
        S += [_ev(db, SUP, "Support Agent reads an assigned ticket (normal).", action="read", resource_accessed="/support/tickets/assigned/T-881", data_sensitivity="LOW"),
              _ev(db, SUP, "Support Agent reads the full customer database.", action="read", resource_accessed="/db/customers/all", data_sensitivity="HIGH"),
              _ev(db, SUP, "Support Agent opens the admin console, unrelated to support.", action="read", resource_accessed="/admin/console", data_sensitivity="MEDIUM")]
    elif name == "devops_credentials":
        touched = [DEV]; _prep(db, DEV)
        S += [_ev(db, DEV, "DevOps Agent reads CPU metrics (normal).", action="read", resource_accessed="/metrics/cpu", data_sensitivity="LOW"),
              _grant(db, DEV, "DevOps Agent unexpectedly obtains production admin permissions.", ["prod_admin"], ["/prod/*"]),
              _ev(db, DEV, "DevOps Agent attempts to read production database credentials.", action="read", resource_accessed="/secrets/prod/db-password", data_sensitivity="CRITICAL")]
    elif name == "procurement_abuse":
        touched = [PRO]; _prep(db, PRO)
        S += [_ev(db, PRO, "Procurement Agent reads supplier info (normal).", action="read", resource_accessed="/db/suppliers/info/acme", data_sensitivity="LOW"),
              _grant(db, PRO, "Procurement Agent obtains purchase-approval privileges beyond its limits.", ["approve_purchase"], ["/api/purchase-approvals/*"]),
              _ev(db, PRO, "Agent approves a purchase order above its approved limit.", action="approve_purchase", resource_accessed="/api/purchase-approvals/PO-9", data_sensitivity="HIGH"),
              _ev(db, PRO, "Agent attempts to change supplier bank details.", action="modify_supplier_bank", resource_accessed="/db/suppliers/bank/acme", data_sensitivity="CRITICAL")]
    elif name == "attack_chain":
        touched = [SUP, FIN, PRO]; _prep(db, SUP, FIN, PRO)
        S += [_ev(db, SUP, "Support Agent reads an assigned ticket (entry, looks normal).", action="read", resource_accessed="/support/tickets/assigned/T-990", data_sensitivity="LOW"),
              _ev(db, SUP, "Support Agent reads customer billing data outside its scope.", action="read", resource_accessed="/db/customers/billing", data_sensitivity="HIGH"),
              _ev(db, FIN, "Finance Agent, acting on a request from Support Agent, reads the same billing data.", action="read", resource_accessed="/db/customers/billing", data_sensitivity="HIGH", parent_agent_id=SUP),
              _ev(db, FIN, "Finance Agent attempts an unauthorized payment approval, still on Support's request.", action="approve_payment", resource_accessed="/finance/payments/batch-9", data_sensitivity="CRITICAL", parent_agent_id=SUP),
              _ev(db, PRO, "Procurement Agent, delegated by Finance Agent, attempts to change supplier bank details.", action="modify_supplier_bank", resource_accessed="/db/suppliers/bank/acme", data_sensitivity="CRITICAL", parent_agent_id=FIN)]
    else:
        raise ValueError(f"Unknown scenario '{name}'")
    if auto_recover:
        _auto_recover(db, touched, S)
    return SimulateResult(scenario=name, agent_id=touched[0], steps=S)


def reset_all(db: Session):
    from .models import AlertModel, AuditLogModel as AL, IncidentModel
    for m in (AlertModel, IncidentModel, EventModel, PermissionChangeModel, AL):
        db.query(m).delete()
    db.commit()
    seed.sync_agents(db)
    for a in db.query(AgentModel).all():
        seed.restore_agent(db, a, to_seed=True)
        a.risk_score = 0.0
    db.add(AL(actor="system", action_taken="SYSTEM_RESET", details="All demo data cleared; agents restored to seed baselines."))
    db.commit()
