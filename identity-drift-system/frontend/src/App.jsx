import React, { useCallback, useEffect, useState } from 'react';
import IntroSequence from './components/IntroSequence.jsx';
import Navbar from './components/Navbar.jsx';
import Sidebar from './components/Sidebar.jsx';
import { Modal, Button } from './components/ui';
import Dashboard from './features/dashboard/Dashboard.jsx';
import AgentFleet from './features/agents/AgentFleet.jsx';
import ActivityStream from './features/events/ActivityStream.jsx';
import AlertsPanel from './features/alerts/AlertsPanel.jsx';
import AuditLog from './features/alerts/AuditLog.jsx';
import SimulatorDeck from './features/simulator/SimulatorDeck.jsx';
import AgentDetail from './features/agents/AgentDetail.jsx';
import ChainView from './features/chains/ChainView.jsx';
import Incidents from './features/incidents/Incidents.jsx';
import { getData } from './services/api';

export default function App() {
  const [intro, setIntro] = useState(true);
  const [menu, setMenu] = useState(false);
  const [view, setView] = useState('overview');
  const [contact, setContact] = useState(false);
  const [agentId, setAgentId] = useState(null);
  const [incId, setIncId] = useState(null);
  const [state, setState] = useState({ agents: [], events: [], alerts: [], audit: [] });
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    const [a, e, al, au] = await Promise.all([getData('/agents', []), getData('/events?limit=100', []), getData('/alerts', []), getData('/audit', [])]);
    setState((s) => ({ agents: a.error ? s.agents : a.data, events: e.error ? s.events : e.data, alerts: al.error ? s.alerts : al.data, audit: au.error ? s.audit : au.data }));
    setError(a.error || e.error || al.error || au.error);
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 2500); return () => clearInterval(t); }, [refresh]);

  const select = (v) => { setView(v); setMenu(false); if (v === 'incidents') setIncId(null); };
  const openAgent = (id) => { setAgentId(id); setView('agent'); };
  const openIncident = (id) => { setIncId(id); setView('incidents'); };
  const views = {
    overview: <Dashboard {...state} healthy={!error} />,
    fleet: <AgentFleet agents={state.agents} refresh={refresh} onOpen={openAgent} />,
    agent: agentId && <AgentDetail key={agentId} id={agentId} refresh={refresh} onBack={() => setView('fleet')} onIncident={openIncident} />,
    chains: <ChainView onIncident={openIncident} />,
    incidents: <Incidents key={incId || 'all'} agents={state.agents} initialId={incId} />,
    activity: <ActivityStream events={state.events} agents={state.agents} />,
    alerts: <AlertsPanel alerts={state.alerts} refresh={refresh} />,
    simulator: <SimulatorDeck refresh={refresh} />,
    audit: <AuditLog audit={state.audit} />,
  };
  return (
    <>
      {intro && <IntroSequence onDone={() => setIntro(false)} />}
      <Navbar open={menu} onToggle={() => setMenu(!menu)} onContact={() => setContact(true)} />
      <Sidebar open={menu} view={view} onSelect={select} onClose={() => setMenu(false)} />
      <main className="max-w-6xl mx-auto px-6 pt-24 pb-16">
        {error && <div className="card mb-4 !border-rose-500/50 mono text-rose-300">⚠ {error} — showing last known data</div>}
        {views[view]}
      </main>
      <Modal open={contact} onClose={() => setContact(false)}>
        <div className="text-lg font-semibold mb-2">Contact</div>
        <p className="text-sm opacity-80 mb-4">Hackathon prototype — simulated events only, no real corporate systems are connected.</p>
        <Button onClick={() => setContact(false)}>Close</Button>
      </Modal>
    </>
  );
}
