import React, { useState } from 'react';
import { Card, Button, SectionTitle } from '../../components/ui';
import { post } from '../../services/api';

const SCENARIOS = [
  ['normal', 'Normal Procurement', 'Alpha agent: price lookup + purchase request. ALLOWED, risk 0.'],
  ['drift', 'Malicious Drift Attack', 'Alpha agent: injected PDF → HR salary read → exfiltration. BLOCKED + contained.'],
  ['update', 'Legitimate Role Update', 'Admin approves a new duty and the baseline; no false alarms.'],
  ['finance_escalation', 'Finance privilege escalation', 'Finance Agent silently gains payment approval, then uses it.'],
  ['hr_anomaly', 'HR data access anomaly', 'HR Agent reads confidential salaries and gains HR admin.'],
  ['support_drift', 'Support access drift', 'Support Agent reads the customer DB and admin console.'],
  ['devops_credentials', 'DevOps credential attempt', 'DevOps Agent obtains prod admin, reads production secrets.'],
  ['procurement_abuse', 'Procurement permission abuse', 'Procurement Agent approves beyond limits, edits supplier bank details.'],
  ['attack_chain', 'Multi-agent attack chain', 'Support → Finance → Procurement via delegation to the same sensitive resources.'],
];

export default function SimulatorDeck({ refresh }) {
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);
  const [auto, setAuto] = useState(false);
  const push = (l) => setLog((p) => [...p, ...[].concat(l)]);
  const run = async (s) => {
    setBusy(true); push(`> POST /events/simulate { scenario: "${s}", auto_recover: ${auto} }`);
    try {
      const r = await post('/events/simulate', { scenario: s, auto_recover: auto });
      r.steps.forEach((st) => {
        push(`  ${st.message}`);
        if (st.result) { const e = st.result.event; push(`    → ${e.action} ${e.resource_accessed}${e.destination ? ' ⇒ ' + e.destination : ''} | risk ${e.risk_score.toFixed(0)} | ${e.outcome}`); }
        if (st.result?.alert) push(`    ⚠ ${st.result.alert.explanation}`);
      });
      push('  ✔ Done. See Fleet, Radar Alerts, Attack Chains and Incidents.'); await refresh();
    } catch (e) { push(`  ✖ ${e.friendly}`); } finally { setBusy(false); }
  };
  const reset = async () => {
    setBusy(true);
    try { await post('/events/reset', {}); setLog(['> RESET: all events, alerts, incidents and audit rows cleared; agents restored to seed baselines.']); await refresh(); }
    catch (e) { push(`  ✖ ${e.friendly}`); } finally { setBusy(false); }
  };
  return (
    <div>
      <SectionTitle n="05 / Simulation deck" right={<div className="flex gap-3 items-center"><label className="mono flex gap-2 items-center"><input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> auto-recover</label><Button disabled={busy} onClick={reset}>Reset demo data</Button></div>}>Scenario control</SectionTitle>
      <div className="grid md:grid-cols-3 gap-4 mb-4">
        {SCENARIOS.map(([id, t, d]) => (
          <Card key={id}><div className="font-semibold">{t}</div><p className="text-xs opacity-70 my-3">{d}</p><Button solid disabled={busy} onClick={() => run(id)}>Run <span className="arrow">→</span></Button></Card>
        ))}
      </div>
      <Card className="!bg-black"><div className="flex justify-between mb-2"><span className="tiny">Console (simulation mode)</span><button className="tiny" onClick={() => setLog([])}>clear</button></div>
        <pre className="mono !normal-case whitespace-pre-wrap min-h-[200px] text-green-400">{log.join('\n') || '// awaiting scenario…'}</pre></Card>
    </div>
  );
}
