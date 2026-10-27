import React, { useEffect, useRef } from 'react';

const PILLS = [['EDR ACTIVE', 12, 20], ['SIEM', 70, 14], ['IAM SYNC', 80, 66], ['RISK 07 HIGH', 22, 74]];

export default function NetworkGraph() {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current, ctx = cv.getContext('2d');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let w, h, raf, mouse = { x: -999, y: -999 };
    const seed = (i) => { const x = Math.sin(i * 127.1) * 43758.5453; return x - Math.floor(x); };
    const nodes = Array.from({ length: 46 }, (_, i) => ({ bx: seed(i + 1), by: seed(i + 99), p: seed(i + 7) * 6.28, x: 0, y: 0 }));
    const resize = () => {
      const dpr = window.devicePixelRatio || 1, r = cv.getBoundingClientRect();
      w = r.width; h = r.height; cv.width = w * dpr; cv.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const draw = (t) => {
      ctx.clearRect(0, 0, w, h);
      nodes.forEach((n) => {
        let x = n.bx * w + Math.sin(t / 1500 + n.p) * 14, y = n.by * h + Math.cos(t / 1800 + n.p) * 14;
        const dx = x - mouse.x, dy = y - mouse.y, d = Math.hypot(dx, dy);
        if (d < 120) { x += (dx / d) * (120 - d) * .5; y += (dy / d) * (120 - d) * .5; }
        n.x = x; n.y = y;
      });
      for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
        const d = Math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y);
        if (d < 140) { ctx.strokeStyle = `rgba(112,117,255,${(1 - d / 140) * .22})`; ctx.beginPath(); ctx.moveTo(nodes[i].x, nodes[i].y); ctx.lineTo(nodes[j].x, nodes[j].y); ctx.stroke(); }
      }
      nodes.forEach((n, i) => { ctx.fillStyle = i % 9 === 0 ? '#22c55e' : '#7075ff'; ctx.beginPath(); ctx.arc(n.x, n.y, i % 9 === 0 ? 3 : 1.8, 0, 6.28); ctx.fill(); });
      if (!reduced) raf = requestAnimationFrame(draw);
    };
    const move = (e) => { const r = cv.getBoundingClientRect(); mouse = { x: e.clientX - r.left, y: e.clientY - r.top }; };
    resize(); raf = requestAnimationFrame(draw);
    window.addEventListener('resize', resize); cv.addEventListener('pointermove', move);
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); cv.removeEventListener('pointermove', move); };
  }, []);
  return (
    <div id="networkPanel" className="card relative overflow-hidden !p-0" style={{ height: 300 }}>
      <canvas ref={ref} className="w-full h-full block" />
      {PILLS.map(([t, x, y]) => <span key={t} className="pill-meta" style={{ left: `${x}%`, top: `${y}%` }}>{t}</span>)}
    </div>
  );
}
