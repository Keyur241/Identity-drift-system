import React, { useState } from 'react';
import { Card, Badge, Button, Gauge, SectionTitle } from '../../components/ui';
import { post } from '../../services/api';

const HEALTH = { Healthy: 'ACTIVE', Monitoring: 'MEDIUM', 'At Risk': 'HIGH', Contained: 'CONTAINED' };

export default function AgentFleet({ agents, refresh, onOpen }) {
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(null);
  const toggle = async (a) => {
    setBusy(a.id); setErr(null);
    try { await post(`/agents/${a.id}/containment`, { action: a.status === 'ACTIVE' ? 'isolate' : 'release' }); await refresh(); }
    catch (e) { setErr(e.friendly); } finally { setBusy(null); }
  };
  return (
    <div>
      <SectionTitle n="02 / Fleet">Monitored agent fleet</SectionTitle>
      {err && <div className="badge b-rose mb-3 inline-block">{err}</div>}
      {!agents.length && <Card><span className="mono">No agents loaded.</span></Card>}
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {agents.map((a) => (
          <Card key={a.id}>
            <div className="flex justify-between items-start gap-2">
              <div><div className="text-lg font-semibold">{a.name}</div><div className="mono opacity-60">{a.declared_role}</div></div>
              <span className={`badge ${a.health === 'Healthy' ? 'b-green' : a.health === 'Monitoring' ? 'b-amber' : 'b-rose'}`}>{a.health}</span>
            </div>
            <p className="text-xs opacity-70 mt-3 min-h-[32px]">{a.description}</p>
            <div className="flex items-center gap-3 mt-3"><span className="text-2xl font-bold w-10">{Math.round(a.risk_score || 0)}</span><div className="flex-1"><Gauge value={a.risk_score || 0} /></div></div>
            <div className="mono mt-2 opacity-70">Session: {a.session_active === false ? 'REVOKED (sim)' : 'active'} · {a.status}</div>
            <div className="flex gap-2 mt-4 flex-wrap">
              <Button solid onClick={() => onOpen(a.id)}>Details <span className="arrow">→</span></Button>
              <Button disabled={busy === a.id} onClick={() => toggle(a)}>{a.status === 'ACTIVE' ? 'Isolate' : 'Release'}</Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
