import React, { useState } from 'react';

const TONE = { ACTIVE: 'b-green', ALLOWED: 'b-green', RESOLVED: 'b-green', LOW: 'b-green',
  CONTAINED: 'b-rose', BLOCKED: 'b-rose', CRITICAL: 'b-rose', HIGH: 'b-rose', OPEN: 'b-rose',
  MEDIUM: 'b-amber', PENDING_REVIEW: 'b-amber', SUSPENDED: 'b-amber', FALSE_POSITIVE: 'b-violet' };

export const Badge = ({ v }) => <span className={`badge ${TONE[v] || 'b-violet'}`}>{String(v).replace('_', ' ')}</span>;
export const Card = ({ className = '', children }) => <div className={`card ${className}`}>{children}</div>;
export const Button = ({ solid, className = '', children, ...p }) => (
  <button className={`btn ${solid ? 'btn-solid' : ''} ${className}`} {...p}>{children}</button>
);
export const Modal = ({ open, onClose, children }) => open ? (
  <div className="fixed inset-0 z-[70] grid place-items-center bg-black/70" onClick={onClose}>
    <div className="card max-w-lg w-[90vw]" onClick={(e) => e.stopPropagation()}>{children}</div>
  </div>) : null;
export const Gauge = ({ value }) => (
  <div className="gauge"><div style={{ width: `${value}%`, background: value >= 75 ? 'var(--rose)' : value >= 40 ? 'var(--amber)' : 'var(--green)' }} /></div>
);
export const SectionTitle = ({ n, children, right }) => (
  <div className="flex items-end justify-between mb-4">
    <div><div className="tiny">{n}</div><h2 className="text-2xl font-semibold tracking-tight">{children}</h2></div>{right}
  </div>
);

export function AnalyzePill({ onScan, children = 'Analyze' }) {
  const [state, setState] = useState('idle');
  const click = () => {
    setState('scanning'); onScan?.();
    setTimeout(() => setState('done'), 1200);
  };
  return (
    <button className="pill-analyze" onClick={click}>
      <span className="glint" />
      {state === 'scanning' ? 'Scanning…' : state === 'done' ? '● Scan confirmed' : children}
    </button>
  );
}
