import React from 'react';

export default function Navbar({ open, onToggle, onContact }) {
  return (
    <header className="topbar">
      <div className="flex items-center gap-2">
        <svg width="22" height="24" viewBox="0 0 24 26" fill="none" stroke="#7075ff" strokeWidth="1.6">
          <path d="M12 1 2 5v7c0 6 4.2 10.6 10 13 5.8-2.4 10-7 10-13V5L12 1Z" /><path d="m8 12.5 3 3 5-6" stroke="#22c55e" />
        </svg>
        <span className="text-lg font-bold tracking-tight">CyberSentrix</span>
      </div>
      <div className="flex items-center gap-3">
        <button className="btn flex items-center gap-2" onClick={onToggle} aria-expanded={open} aria-controls="menuDrawer">
          Menu <span className={`plus ${open ? 'open' : ''}`}>+</span>
        </button>
        <button className="btn btn-solid" onClick={onContact}>Contact <span className="arrow">→</span></button>
      </div>
    </header>
  );
}
