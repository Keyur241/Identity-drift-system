import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
from fastapi.testclient import TestClient
from app.main import app

AID = "agent-procurement-alpha"


def test_all():
    with TestClient(app) as c:
        r = c.post("/api/events/simulate", json={"scenario": "normal"}).json()
        assert all(s["result"]["event"]["outcome"] == "ALLOWED" and s["result"]["event"]["risk_score"] == 0
                   for s in r["steps"] if s["result"])
        r = c.post("/api/events/simulate", json={"scenario": "drift"}).json()
        outs = [s["result"]["event"]["outcome"] for s in r["steps"]]
        assert outs[0] == "ALLOWED" and outs[1] == "BLOCKED" and outs[2] == "BLOCKED", outs
        assert r["steps"][1]["result"]["event"]["risk_score"] >= 75
        assert r["steps"][2]["result"]["alert"]["risk_score"] == 100
        agent = [a for a in c.get("/api/agents").json() if a["id"] == AID][0]
        assert agent["status"] == "CONTAINED"
        r = c.post("/api/events/simulate", json={"scenario": "update"}).json()
        assert all(s["result"]["event"]["outcome"] == "ALLOWED" for s in r["steps"] if s["result"])
        assert any(a["action_taken"] == "ROLE_PROFILE_UPDATED" for a in c.get("/api/audit").json())
        assert c.get("/api/alerts").json()
    os.remove("test.db")


def test_new_agents_chain_incident_response_reset():
    with TestClient(app) as c:
        c.post("/api/events/reset")
        assert len(c.get("/api/agents").json()) == 6
        r = c.post("/api/events/simulate", json={"scenario": "finance_escalation"}).json()
        assert r["steps"][1]["result"]["alert"]["risk_score"] == 70       # privilege-drift alert
        assert r["steps"][2]["result"]["event"]["outcome"] == "BLOCKED"   # permitted by credentials, never baselined
        fin = c.get("/api/agents/agent-finance/detail").json()
        assert fin["drift"]["added"]["actions"] == ["approve_payment"] and fin["agent"]["health"] == "Contained"
        assert c.post("/api/agents/agent-finance/respond", json={"action": "restore_access"}).json()["status"] == "CONFIRMATION_REQUIRED"
        c.post("/api/agents/agent-finance/respond", json={"action": "restore_access", "confirm": True})
        assert c.get("/api/agents/agent-finance/detail").json()["drift"]["score"] == 0
        c.post("/api/events/simulate", json={"scenario": "attack_chain"})
        ch = c.get("/api/chains").json()
        assert ch and ch[0]["entry_point"]["agent_id"] == "agent-support" and len(ch[0]["agents"]) == 3
        iid = c.get("/api/incidents").json()[0]["id"]
        assert c.patch(f"/api/incidents/{iid}", json={"status": "INVESTIGATING", "note": "looking"}).json()["status"] == "INVESTIGATING"
        assert c.get(f"/api/incidents/{iid}/report?format=csv").text.startswith("incident_id")
        assert c.get(f"/api/incidents/{iid}/report?format=json").json()["agent_id"]
        c.post("/api/events/simulate", json={"scenario": "hr_anomaly", "auto_recover": True})
        assert c.get("/api/incidents?agent_id=agent-hr&status=RESOLVED").json()
