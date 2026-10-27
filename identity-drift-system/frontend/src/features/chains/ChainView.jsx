import React from 'react';
import { Badge, Card, SectionTitle } from '../../components/ui';
import { ts } from '../../services/api';
import { usePoll } from '../../services/hooks';

function Graph({ c }) {
  const W = Math.max(520, c.agents.length * 200), ax = (i) => 90 + i * ((W - 180) / Math.max(1, c.agents.length - 1));
  const rs = c.resources, rx = (i) => 90 + i * ((W - 180) / Math.max(1, rs.length - 1 || 1));
  const aIdx = Object.fromEntries(c.agents.map((a, i) => [a.id, i]));
  const rIdx = Object.fromEntries(rs.map((r, i) => [r, i]));
  const pos = (i, n, f) => (n === 1 ? W / 2 : f(i));
  const AX = (id) => pos(aIdx[id], c.agents.length, ax), RX = (r) => pos(rIdx[r], rs.length, rx);
  const evAgent = Object.fromEntries(c.steps.map((s) => [s.event_id, s]));
  return (
    <div className="overflow-x-auto"><svg viewBox={`0 0 ${W} 230`} width={W} height="230" role="img" aria-label="Attack chain graph">
      <defs><marker id="ar" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 8 4 0 8z" fill="#f43f5e" /></marker></defs>
      {c.steps.map((s) => <g key={s.event_id}><line x1={AX(s.agent_id)} y1="62" x2={RX(s.resource)} y2="170" stroke={s.risk > 0 ? '#7075ff' : '#475569'} strokeOpacity=".7" />
        <text x={(AX(s.agent_id) + RX(s.resource)) / 2 + 4} y={118 + (s.n % 3) * 9} fontSize="9" fill="#e5e8f4" fontFamily="monospace">{s.n}·{s.action}</text></g>)}
      {c.links.filter((l) => l.from_agent !== l.to_agent && evAgent[l.to_event]?.parent_agent_id === l.from_agent).map((l, i) => {
        const x1 = AX(l.from_agent), x2 = AX(l.to_agent); return <path key={i} d={`M${x1} 30 Q${(x1 + x2) / 2} ${-10 - i * 4} ${x2} 30`} fill="none" stroke="#f43f5e" strokeWidth="1.5" markerEnd="url(#ar)" />;
      })}
      {c.agents.map((a) => <g key={a.id}><circle cx={AX(a.id)} cy="46" r="18" fill="#101126" stroke={a.id === c.entry_point.agent_id ? '#f43f5e' : '#7075ff'} strokeWidth="2" />
        <text x={AX(a.id)} y="50" textAnchor="middle" fontSize="10" fill="#fff">{a.name.split(' ')[0]}</text></g>)}
      {rs.map((r) => <g key={r}><rect x={RX(r) - 70} y="170" width="140" height="26" rx="5" fill="#0b0c16" stroke="#22c55e" strokeOpacity=".6" /><text x={RX(r)} y="187" textAnchor="middle" fontSize="9" fill="#e5e8f4" fontFamily="monospace">{r.length > 26 ? r.slice(0, 25) + '…' : r}</text></g>)}
    </svg></div>
  );
}

export default function ChainView({ onIncident }) {
  const { data: chains, error } = usePoll('/chains', [], 3000);
  return (
    <div>
      <SectionTitle n="07 / Attack chains">Multi-agent correlation</SectionTitle>
      {error && <div className="badge b-rose mb-3 inline-block">{error}</div>}
      {!chains.length && <Card><span className="mono">No suspected chains. Run the “Multi-agent attack chain” scenario.</span></Card>}
      <div className="grid gap-4">
        {chains.map((c) => (
          <Card key={c.id}>
            <div className="flex justify-between flex-wrap gap-2"><div className="font-semibold">{c.id} · {c.agents.map((a) => a.name).join(' → ')}</div><div className="flex gap-2"><span className="badge b-amber">{c.status}</span><Badge v={c.severity} /></div></div>
            <p className="text-xs opacity-70 my-2">{c.note}</p>
            <Graph c={c} />
            <div className="mono !normal-case mt-2">Suspected entry point: <b>{c.entry_point.agent_name}</b> (event #{c.entry_point.event_id}) · Affected resources: {c.resources.join(', ')}</div>
            <div className="mono !normal-case">Potentially affected agents: {c.agents.map((a) => `${a.name} (risk ${Math.round(a.risk)})`).join(', ')}</div>
            <div className="tiny mt-3">Evidence</div><ul className="list-disc pl-5 text-xs space-y-1">{c.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
            <div className="overflow-x-auto mt-3"><table className="stream"><thead><tr><th>#</th><th>Time</th><th>Agent</th><th>Action</th><th>Resource</th><th>Risk</th><th>Outcome</th></tr></thead>
              <tbody>{c.steps.map((s) => <tr key={s.event_id}><td>{s.n}</td><td>{ts(s.timestamp)}</td><td>{s.agent_name}{s.parent_agent_id ? ' ↩ delegated' : ''}</td><td>{s.action}</td><td className="break-all">{s.resource}</td><td>{Math.round(s.risk)}</td><td><Badge v={s.outcome} /></td></tr>)}</tbody></table></div>
            {!!c.incident_ids.length && <div className="mt-3 flex gap-2 flex-wrap"><span className="tiny self-center">Incidents:</span>{c.incident_ids.map((i) => <button key={i} className="btn" onClick={() => onIncident(i)}>#{i}</button>)}</div>}
          </Card>))}
      </div>
    </div>
  );
}
