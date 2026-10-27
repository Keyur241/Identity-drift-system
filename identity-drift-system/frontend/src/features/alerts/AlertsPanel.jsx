import React, { useState } from 'react';
import { Card, Badge, Button, Gauge, AnalyzePill, SectionTitle } from '../../components/ui';
import { post, ts } from '../../services/api';

const COLOR = { CRITICAL: '#f43f5e', HIGH: '#f97316', MEDIUM: '#eab308', LOW: '#22c55e' };

function Radar({ alerts }) {
  return (
    <div className="radar-hud" aria-label="Radar of open alerts">
      <div className="ring r3" /><div className="ring" /><div className="ring r2" /><div className="cross-h" /><div className="cross-v" /><div className="sweep" />
      {alerts.filter((a) => a.status === 'OPEN').slice(0, 14).map((a) => {
        const ang = (a.id * 137.5) * Math.PI / 180, r = 12 + (100 - a.risk_score) * .36;
        return <span key={a.id} className="blip" style={{ left: `${50 + Math.cos(ang) * r}%`, top: `${50 + Math.sin(ang) * r}%`, color: COLOR[a.severity] }} title={`#${a.id} ${a.severity}`} />;
      })}
    </div>
  );
}

function AlertCard({ a, refresh, setErr }) {
  const [show, setShow] = useState(false);
  const act = async (status) => { try { await post(`/alerts/${a.id}/resolve`, { status }); await refresh(); } catch (e) { setErr(e.friendly); } };
  return (
    <Card>
      <div className="flex justify-between items-center"><span className="mono">Alert #{a.id} · {ts(a.timestamp)}</span><div className="flex gap-2"><Badge v={a.severity} /><Badge v={a.status} /></div></div>
      <div className="flex items-center gap-3 mt-3"><span className="text-3xl font-bold w-14">{a.risk_score.toFixed(0)}</span><div className="flex-1"><Gauge value={a.risk_score} /></div></div>
      <p className="text-sm mt-3 leading-relaxed opacity-90">{a.explanation}</p>
      <div className="mt-3 flex flex-wrap gap-2 items-center">
        <AnalyzePill onScan={() => setShow(true)} />
        {a.status === 'OPEN' && <><Button onClick={() => act('RESOLVED')}>Resolve</Button><Button onClick={() => act('FALSE_POSITIVE')}>False positive</Button></>}
      </div>
      {show && <ul className="mt-3 list-disc pl-5 text-xs space-y-1 opacity-80">{a.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>}
    </Card>
  );
}

export default function AlertsPanel({ alerts, refresh }) {
  const [err, setErr] = useState(null);
  return (
    <div>
      <SectionTitle n="04 / Radar alerts">Explainable risk</SectionTitle>
      {err && <div className="badge b-rose mb-3 inline-block">{err}</div>}
      <div className="flex gap-6 flex-wrap lg:flex-nowrap">
        <Radar alerts={alerts} />
        <div className="grid gap-4 flex-1">
          {alerts.map((a) => <AlertCard key={a.id} a={a} refresh={refresh} setErr={setErr} />)}
          {!alerts.length && <Card><span className="mono">No alerts. Fleet is behaving within declared roles.</span></Card>}
        </div>
      </div>
    </div>
  );
}
