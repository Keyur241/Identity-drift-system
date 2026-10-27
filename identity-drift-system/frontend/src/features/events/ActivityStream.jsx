import React, { useEffect, useRef } from 'react';
import { Badge, Card, SectionTitle } from '../../components/ui';
import { ts } from '../../services/api';

function MatrixRain() {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current, ctx = cv.getContext('2d');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let raf; const cols = 40, fs = 12, speeds = Array.from({ length: cols }, () => .3 + Math.random() * .9), ys = Array.from({ length: cols }, () => Math.random() * 40);
    cv.width = cols * fs; cv.height = 90;
    const draw = () => {
      ctx.fillStyle = 'rgba(7,7,11,.12)'; ctx.fillRect(0, 0, cv.width, cv.height);
      ctx.font = `${fs - 2}px monospace`; ctx.fillStyle = '#7075ff';
      ys.forEach((y, i) => { ctx.fillText(Math.random() > .5 ? '1' : '0', i * fs, y * fs); ys[i] = y * fs > cv.height + 40 ? 0 : y + speeds[i] * .25; });
      if (!reduced) raf = requestAnimationFrame(draw);
    };
    draw(); return () => cancelAnimationFrame(raf);
  }, []);
  return <canvas ref={ref} className="w-full rounded-lg opacity-60 mb-4" style={{ height: 90 }} />;
}

export default function ActivityStream({ events, agents }) {
  const names = Object.fromEntries(agents.map((a) => [a.id, a.name]));
  return (
    <div>
      <SectionTitle n="03 / Activity stream" right={<span className="mono text-green-400">● live · 2.5s poll</span>}>Agent activity</SectionTitle>
      <MatrixRain />
      <Card className="overflow-x-auto !p-2">
        <table className="stream">
          <thead><tr><th>Time</th><th>Agent</th><th>Action</th><th>Resource</th><th>Dest</th><th>Sens.</th><th>Risk</th><th>Outcome</th></tr></thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{ts(e.timestamp)}</td><td title={e.agent_id}>{names[e.agent_id] || e.agent_id}</td><td>{e.action}</td>
                <td className="break-all">{e.resource_accessed}</td><td>{e.destination || '—'}</td>
                <td><Badge v={e.data_sensitivity} /></td><td>{e.risk_score.toFixed(0)}</td><td><Badge v={e.outcome} /></td>
              </tr>
            ))}
            {!events.length && <tr><td colSpan="8">No events yet — run a scenario.</td></tr>}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
