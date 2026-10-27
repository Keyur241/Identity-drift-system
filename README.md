# Identity Drift Detection in Autonomous AI Agents (hackathon prototype)

Rule-based detector for AI agents that keep valid credentials but act outside their declared role. All events are **simulated**; nothing connects to real systems, and no accuracy is claimed.

## Run
```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # http://localhost:8000/docs  (tables auto-created on startup; no migrations needed)
pytest test_scenarios.py           # optional: pip install pytest

# Frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## Scoring
base (LOW 10 / MEDIUM 30 / HIGH 60 / CRITICAL 90) + 20 role mismatch + 30 unapproved destination, capped at 100; clean events score 0.
≥75 → BLOCKED + agent CONTAINED + audit entry; ≥40 → PENDING_REVIEW. Contained agents' clean events go to PENDING_REVIEW.

## Spec vs. assumptions
Required by brief: role profiles, event log, detector, explainable alerts, simulated containment, audit trail, dashboard.
Our choices: SQLite, thresholds/severity bands, the `fnmatch` wildcard rules, the three scenarios.
Not implemented: statistical/ML baselines, gradual-drift and multi-agent chain analysis (parent_agent_id is stored only).

## v2 additions (all SIMULATION mode — no real accounts, tokens or sessions are touched)
- **6 monitored agents** (original Procurement Agent Alpha + Finance, HR, Customer Support, DevOps, Procurement). Each has a baseline (expected role/actions/resources/destinations), current permissions, independent risk score and health (Healthy / Monitoring / At Risk / Contained).
- **Drift comparison:** `GET /api/agents/{id}/detail` (expected vs actual, new/removed permissions, drift score). The engine judges events against the *baseline*, so a privilege that credentials allow but nobody approved is still flagged.
- **Attack chains:** `GET /api/chains` links events across agents by delegation (`parent_agent_id`) or shared resource within 30 min. Always labelled SUSPECTED.
- **Response/recovery:** `POST /api/agents/{id}/respond` (contain, revoke_session, restrict_permission, restore_access, approve_baseline); needs `confirm: true`, else returns CONFIRMATION_REQUIRED. Every action is audited.
- **Explanation:** rule-based and deterministic (`llm_used: false`); built only from stored events and permission diffs.
- **Incidents:** `GET/PATCH /api/incidents`, filters (severity, agent_id, status, date_from, date_to), `GET /api/incidents/{id}/report?format=json|csv`.
- **Scenarios** (Simulation Deck or `POST /api/events/simulate`): normal, drift, update, finance_escalation, hr_anomaly, support_drift, devops_credentials, procurement_abuse, attack_chain. `auto_recover: true` also runs investigation → restore → resolve. `POST /api/events/reset` clears demo data and restores seed baselines.
- Existing SQLite DBs are upgraded on startup (`migrate.py` adds columns; new tables are created automatically).
