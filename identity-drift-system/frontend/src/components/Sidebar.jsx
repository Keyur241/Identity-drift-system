import React from 'react';

export const NAV = [['overview', '01', 'Overview'], ['fleet', '02', 'Fleet'], ['activity', '03', 'Activity Stream'],
  ['alerts', '04', 'Radar Alerts'], ['simulator', '05', 'Simulation Deck'], ['audit', '06', 'Audit Log'],
  ['chains', '07', 'Attack Chains'], ['incidents', '08', 'Incidents']];

export default function Sidebar({ open, view, onSelect, onClose }) {
  return (
    <>
      <div className={`backdrop ${open ? 'open' : ''}`} onClick={onClose} />
      <aside id="menuDrawer" className={open ? 'open' : ''} aria-hidden={!open}>
        <div className="tiny mb-4">Catalog index</div>
        {NAV.map(([id, n, label]) => (
          <button key={id} className={`menu-item ${view === id ? 'active' : ''}`} onClick={() => onSelect(id)}>
            <span><span className="mono opacity-50 mr-3">{n}</span>{label}</span><span>↗</span>
          </button>
        ))}
      </aside>
    </>
  );
}
