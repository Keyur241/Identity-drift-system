import React from 'react';
import { Card, SectionTitle } from '../../components/ui';
import { ts } from '../../services/api';

export default function AuditLog({ audit }) {
  return (
    <div>
      <SectionTitle n="06 / Audit log">What happened & what we did</SectionTitle>
      <Card className="overflow-x-auto !p-2">
        <table className="stream"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Details</th></tr></thead>
          <tbody>{audit.map((l) => <tr key={l.id}><td>{ts(l.timestamp)}</td><td>{l.actor}</td><td>{l.action_taken}</td><td>{l.details}</td></tr>)}
            {!audit.length && <tr><td colSpan="4">No audit entries.</td></tr>}</tbody></table>
      </Card>
    </div>
  );
}
