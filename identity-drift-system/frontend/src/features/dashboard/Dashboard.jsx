import React, { useState } from 'react';
import NetworkGraph from './NetworkGraph.jsx';
import { Card, Badge, SectionTitle } from '../../components/ui';

const Metric = ({ label, value, tone }) => (
  <Card><div className="tiny">{label}</div><div className={`text-4xl font-bold mt-1 ${tone || ''}`}>{value}</div></Card>
);

export default function Dashboard({ agents, events, alerts, healthy }) {
  const [open, setOpen] = useState(false);
  const openAlerts = alerts.filter((a) => a.status === 'OPEN');
  const top = [...openAlerts].sort((a, b) => b.risk_score - a.risk_score)[0];
  return (
    <div>
      <SectionTitle n="01 / Overview">Agent identity posture</SectionTitle>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <Metric label="Monitored agents" value={agents.length} />
        <Metric label="Active threats" value={openAlerts.length} tone={openAlerts.length ? 'text-rose-400' : 'text-green-400'} />
        <Metric label="Blocked events" value={events.filter((e) => e.outcome === 'BLOCKED').length} />
        <Metric label="System health" value={healthy ? 'NOMINAL' : 'DEGRADED'} tone={healthy ? 'text-green-400 !text-2xl' : 'text-amber-400 !text-2xl'} />
      </div>
      <NetworkGraph />
      <Card className="mt-4">
        <button className="w-full flex justify-between items-center text-left" onClick={() => setOpen(!open)} aria-expanded={open}>
          <div><div className="tiny">Featured insight</div>
            <div className="text-lg font-semibold">{top ? `Highest open risk: ${top.risk_score}/100` : 'No open drift alerts — fleet within declared roles'}</div></div>
          <span className="text-2xl transition-transform duration-500" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0)' }}>→</span>
        </button>
        {open && <p className="mt-3 text-sm opacity-80 leading-relaxed">{top ? top.explanation : 'Valid credentials do not prove intended behaviour. Run the Simulation Deck to see a Procurement Agent drift after an indirect prompt injection and get contained automatically.'}</p>}
        {top && <div className="mt-2"><Badge v={top.severity} /></div>}
      </Card>
    </div>
  );
}
