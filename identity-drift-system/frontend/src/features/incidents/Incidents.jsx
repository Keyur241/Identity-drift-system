import React, { useState } from 'react';
import { Badge, Button, Card, SectionTitle } from '../../components/ui';
import { download, patch, ts } from '../../services/api';
import { usePoll } from '../../services/hooks';

const STATUSES = ['NEW', 'INVESTIGATING', 'CONFIRMED_THREAT', 'FALSE_POSITIVE', 'RESOLVED'];
const sel = 'bg-midnight border border-violet/40 rounded-full px-3 py-1 mono !normal-case text-ice';

function Detail({ id, refresh }) {
  const { data: d, error } = usePoll(`/incidents/${id}`, null, 3000);
  const [note, setNote] = useState('');
  const [err, setErr] = useState(null);
  if (!d) return <Card><span className="mono">{error || 'Loading…'}</span></Card>;
  const upd = async (body) => { try { await patch(`/incidents/${id}`, body); setNote(''); setErr(null); refresh(); } catch (e) { setErr(e.friendly); } };
  const dl = (fmt) => download(`/incidents/${id}/report?format=${fmt}`, `incident-${id}.${fmt}`).catch((e) => setErr(e.friendly));
  return (
    <Card>
      <div className="flex justify-between flex-wrap gap-2"><div><div className="tiny">Incident #{d.id} · {d.agent_id}</div><div className="text-xl font-semibold">{d.title}</div></div><div className="flex gap-2 h-fit"><Badge v={d.severity} /><span className="mono self-center">risk {Math.round(d.risk_score)}</span></div></div>
      <p className="text-sm opacity-80 my-3">{d.summary}</p>
      {err && <div className="badge b-rose mb-2 inline-block">{err}</div>}
      <div className="flex gap-2 flex-wrap items-center">
        <select className={sel} value={d.status} onChange={(e) => upd({ status: e.target.value })} aria-label="Status">{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        <Button onClick={() => dl('json')}>Export JSON</Button><Button onClick={() => dl('csv')}>Export CSV</Button>
        {d.chain_ids.map((c) => <span key={c} className="badge b-amber">{c}</span>)}
      </div>
      <div className="flex gap-2 my-3"><input className={`${sel} flex-1`} placeholder="Add investigation note…" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button disabled={!note.trim()} onClick={() => upd({ note })}>Add note</Button></div>
      <div className="grid lg:grid-cols-2 gap-4">
        <div><div className="tiny mb-1">Timeline</div><ul className="space-y-1 max-h-72 overflow-auto">{d.timeline.map((t, i) => <li key={i} className="text-xs"><span className="mono">{ts(t.ts)} · {t.type}</span> {t.text}</li>)}</ul></div>
        <div><div className="tiny mb-1">Risk factors (rule-based)</div><ul className="space-y-1 max-h-72 overflow-auto">{d.explanation.factors.map((f, i) => <li key={i} className="text-xs"><Badge v={f.severity} /> +{Math.round(f.points)} {f.description}</li>)}</ul>
          <div className="tiny mt-3 mb-1">Response actions (simulated)</div><ul className="text-xs space-y-1">{d.actions.map((a, i) => <li key={i}>{ts(a.ts)} · {a.actor}: {a.action} — {a.detail}</li>)}{!d.actions.length && <li className="mono">None yet.</li>}</ul></div>
      </div>
    </Card>
  );
}

export default function Incidents({ agents, initialId }) {
  const [f, setF] = useState({ severity: '', agent_id: '', status: '', date_from: '' });
  const [open, setOpen] = useState(initialId || null);
  const [tick, setTick] = useState(0);
  const qs = Object.entries(f).filter(([, v]) => v).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
  const { data: list, error } = usePoll(`/incidents?${qs}&_=${tick}`, [], 3000);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div>
      <SectionTitle n="08 / Incidents">Investigation & reporting</SectionTitle>
      <div className="flex gap-2 flex-wrap mb-4 items-center">
        <select className={sel} value={f.severity} onChange={set('severity')} aria-label="Severity"><option value="">All severities</option>{['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => <option key={s}>{s}</option>)}</select>
        <select className={sel} value={f.agent_id} onChange={set('agent_id')} aria-label="Agent"><option value="">All agents</option>{agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select>
        <select className={sel} value={f.status} onChange={set('status')} aria-label="Status filter"><option value="">All statuses</option>{STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        <input type="date" className={sel} value={f.date_from} onChange={set('date_from')} aria-label="From date" />
        <Button onClick={() => setF({ severity: '', agent_id: '', status: '', date_from: '' })}>Clear</Button>
      </div>
      {error && <div className="badge b-rose mb-3 inline-block">{error}</div>}
      <Card className="overflow-x-auto !p-2 mb-4"><table className="stream"><thead><tr><th>ID</th><th>Agent</th><th>Severity</th><th>Risk</th><th>Status</th><th>Updated</th><th /></tr></thead>
        <tbody>{list.map((i) => <tr key={i.id}><td>#{i.id}</td><td>{i.agent_name}</td><td><Badge v={i.severity} /></td><td>{Math.round(i.risk_score)}</td><td><Badge v={i.status} /></td><td>{ts(i.updated_at)}</td><td><button className="btn" onClick={() => setOpen(i.id)}>Open</button></td></tr>)}
          {!list.length && <tr><td colSpan="7">No incidents match. Run a scenario from the Simulation Deck.</td></tr>}</tbody></table></Card>
      {open && <Detail id={open} refresh={() => setTick((t) => t + 1)} />}
    </div>
  );
}
