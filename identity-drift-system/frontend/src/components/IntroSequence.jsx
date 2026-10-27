import React, { useEffect, useState } from 'react';

const FRAMES = [[0, 'Protect'], [900, 'Systems'], [1800, 'Security decisions without the noise'], [3000, 'Own your security']];
const TELE = ['MEMORY_CACHE = []', 'TRACE_ID: CS-2049', 'AGENT_MESH: SYNC', 'IAM: VALID_TOKEN', 'DRIFT_SCORE: 0.00', 'EDR: ACTIVE'];

export default function IntroSequence({ onDone }) {
  const [frame, setFrame] = useState(0);
  const [wipe, setWipe] = useState(false);

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const t = FRAMES.map(([ms], i) => setTimeout(() => setFrame(i), ms));
    const end = setTimeout(() => setWipe(true), reduced ? 300 : 4000);
    const done = setTimeout(onDone, reduced ? 400 : 5000);
    return () => [...t, end, done].forEach(clearTimeout);
  }, [onDone]);

  const skip = () => { setWipe(true); setTimeout(onDone, 900); };
  return (
    <div className={`intro ${wipe ? 'wipe' : ''}`}>
      {TELE.map((t, i) => (
        <span key={t} className="float-tele" style={{ left: `${8 + i * 15}%`, top: `${15 + ((i * 37) % 70)}%`, animationDelay: `${i * .4}s` }}>{t}</span>
      ))}
      <button className="btn absolute top-6 right-6" onClick={skip}>Skip Intro</button>
      <div key={frame} className="kinetic">
        <span className="bracket">[</span> {FRAMES[frame][1]} <span className="bracket">]</span>
      </div>
      <div className="progress" />
    </div>
  );
}
