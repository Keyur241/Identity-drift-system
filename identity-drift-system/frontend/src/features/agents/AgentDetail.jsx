import React, { useState } from 'react';
import { Card, Badge, Button, Gauge, Modal, SectionTitle } from '../../components/ui';
import { post, ts } from '../../services/api';
import { usePoll } from '../../services/hooks';

const LABEL = { contain: 'Contain agent', revoke_session: 'Revoke session', restrict_permission: 'Restrict permission', restore_access: 'Restore access (rollback to baseline)', approve_baseline: 'Approve as new baseline' };

function PermList({ title, expected, actual, added, removed }) {
  return (
    <div>
      <div className="tiny mb-1">{title}</div>
      <div className="grid grid-cols-2 gap-3">
        <div><div className="tiny">Expected (baseline)</div>{expected.map((x) => <div key={x} className="mono !normal-case break-all">{x}{removed.includes(x) && <span className="text-amber-400"> · REMOVED</span>}</div>)}{!expected.length && <div className="mono">—</div>}</div>
        <div><div className="tiny">Actual (current)</div>{actual.map((x) => <div key={x} className={`mono !normal-case break-all ${added.includes(x) ? 'text-rose-400' : ''}`}>{x}{added.includes(x) && ' · NEW ⚠'}</div>)}{!actual.length && <div className="mono">—</div>}</div>
      </div>
    </div>
  );
}

export default function AgentDetail({ id, onBack, refresh, onIncident }) {
  const { data, error } = usePoll(`/agents/${id}/detail`, null, 3000);
  const { data: events } = usePoll(`/events?limit=15&agent_id=${id}`, [], 3000);
  const [pending, setPending] = useState(null);
  const [msg, setMsg] = useState(null);
  if (!data) return <Card><Button onClick={onBack}>← Fleet</Button><p className="mono mt-3">{error || 'Loading…'}</p></Card>;
  const { agent, drift, explanation: ex, incidents } = data;
  const added = (k) => drift.added[k], removed = (k) => drift.removed[k];
  const allAdded = ['actions', 'resources', 'destinations'].flatMap((k) => drift.added[k]);
  const run = async () => {
    try { const r = await post(`/agents/${id}/respond`, { action: pending.action, permission: pending.permission, confirm: true }); setMsg(r.message); await refresh(); }
    catch (e) { setMsg(`✖ ${e.friendly}`); } finally { setPending(null); }
  };
  const ask = (action, permission) => setPending({ action, permission });
  return (
    <div>
      <Button onClick={onBack}>← Fleet</Button>
      <SectionTitle n={`Agent ${agent.id}`} right={<span className={`badge ${agent.health === 'Healthy' ? 'b-green' : agent.health === 'Monitoring' ? 'b-amber' : 'b-rose'}`}>{agent.health}</span>}>{agent.name}</SectionTitle>
      <p className="text-sm opacity-80 mb-3">{agent.description}</p>
      {msg && <div className="card mb-4 mono !normal-case text-green-300">{msg}</div>}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <div className="tiny">Identity drift comparison</div>
          <div className="flex items-center gap-3 my-2"><span className="text-3xl font-bold">{drift.score}</span><div className="flex-1"><Gauge value={drift.score} /></div><Badge v={drift.severity === 'NONE' ? 'LOW' : drift.severity} /></div>
          <div className="mono !normal-case mb-3">Role: expected <b>{drift.role_expected}</b> · actual <b className={drift.role_expected !== drift.role_actual ? 'text-rose-400' : ''}>{drift.role_actual}</b></div>
          <div className="space-y-4">
            <PermList title="Actions" expected={drift.expected.actions} actual={drift.actual.actions} added={added('actions')} removed={removed('actions')} />
            <PermList title="Resources" expected={drift.expected.resources} actual={drift.actual.resources} added={added('resources')} removed={removed('resources')} />
            <PermList title="Destinations" expected={drift.expected.destinations} actual={drift.actual.destinations} added={added('destinations')} removed={removed('destinations')} />
          </div>
          {!drift.factors.length && <p className="mono mt-3 text-green-400">No drift: current permissions match the approved baseline.</p>}
          {!!agent.restricted_permissions?.length && <p className="mono !normal-case mt-3">Restricted by response: {agent.restricted_permissions.join(', ')}</p>}
        </Card>
        <Card>
          <div className="tiny">Risk explanation · {ex.method}{ex.llm_used ? '' : ' · no LLM used'}</div>
          <div className="flex items-center gap-3 my-2"><span className="text-3xl font-bold">{Math.round(ex.risk_score)}</span><div className="flex-1"><Gauge value={ex.risk_score} /></div></div>
          <p className="text-sm leading-relaxed mb-3">{ex.summary}</p>
          <div className="tiny mb-1">Contributing factors</div>
          <ul className="space-y-2 max-h-56 overflow-auto">
            {ex.factors.map((f, i) => <li key={i} className="text-xs"><Badge v={f.severity} /> <span className="mono">+{Math.round(f.points)} · {f.source}</span> <span className="opacity-80">{f.description}</span></li>)}
            {!ex.factors.length && <li className="mono">No contributing factors.</li>}
          </ul>
        </Card>
        <Card>
          <div className="tiny">Recommended response (simulation only · confirmation required)</div>
          <ul className="my-3 space-y-2">
            {ex.recommendations.map((r, i) => (
              <li key={i} className="flex justify-between gap-3 items-start text-xs">
                <span><Badge v={r.urgency === 'IMMEDIATE' ? 'CRITICAL' : r.urgency === 'HIGH' ? 'HIGH' : 'MEDIUM'} /> <b>{LABEL[r.action] || 'Monitor'}</b>{r.permission && ` · ${r.permission}`}<br /><span className="opacity-70">{r.reason}</span></span>
                {r.action !== 'monitor' && <Button onClick={() => ask(r.action, r.permission)}>Apply</Button>}
              </li>))}
          </ul>
          <div className="flex gap-2 flex-wrap">
            <Button onClick={() => ask('contain')}>Contain</Button><Button onClick={() => ask('revoke_session')}>Revoke session</Button>
            <Button onClick={() => ask('restore_access')}>Restore access</Button><Button onClick={() => ask('approve_baseline')}>Approve baseline</Button>
          </div>
          {!!allAdded.length && <div className="flex gap-2 mt-3 items-center flex-wrap"><span className="tiny">Restrict:</span>{allAdded.map((p) => <Button key={p} onClick={() => ask('restrict_permission', p)}>{p}</Button>)}</div>}
        </Card>
        <Card>
          <div className="tiny">Investigation history</div>
          <ul className="my-2 space-y-2">{incidents.map((i) => <li key={i.id}><button className="text-left text-sm hover:text-violet-300" onClick={() => onIncident(i.id)}>#{i.id} {i.title} <Badge v={i.status} /> <Badge v={i.severity} /></button></li>)}
            {!incidents.length && <li className="mono">No incidents.</li>}</ul>
          <div className="tiny mt-4">Recent activity</div>
          <table className="stream"><tbody>{events.map((e) => <tr key={e.id}><td>{ts(e.timestamp)}</td><td>{e.action}</td><td className="break-all">{e.resource_accessed}</td><td><Badge v={e.outcome} /></td></tr>)}
            {!events.length && <tr><td>No events.</td></tr>}</tbody></table>
        </Card>
      </div>
      <Modal open={!!pending} onClose={() => setPending(null)}>
        <div className="text-lg font-semibold mb-2">Confirm: {pending && LABEL[pending.action]}</div>
        <p className="text-sm opacity-80 mb-1">{agent.name}{pending?.permission ? ` · ${pending.permission}` : ''}</p>
        <p className="text-sm opacity-80 mb-4">This is a <b>simulation</b>: only local CyberSentrix state changes; no real account, token or session is affected. The action is written to the audit log.</p>
        <div className="flex gap-2"><Button solid onClick={run}>Confirm</Button><Button onClick={() => setPending(null)}>Cancel</Button></div>
      </Modal>
    </div>
  );
}
