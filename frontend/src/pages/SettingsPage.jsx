import { Settings } from 'lucide-react';

export default function SettingsPage({ user }) {
  return (
    <div>
      <div className="dashboard-topbar">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Settings size={18} /> Settings
        </h2>
      </div>
      <div style={{ padding: '2rem 1.5rem', maxWidth: 600 }}>
        <div className="card" style={{ padding: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '0.9375rem', fontWeight: 600 }}>Account</h3>
          {user && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.875rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <span style={{ color: 'var(--text-muted)', minWidth: 80 }}>Name</span>
                <span>{user.name}</span>
              </div>
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <span style={{ color: 'var(--text-muted)', minWidth: 80 }}>Email</span>
                <span>{user.email}</span>
              </div>
            </div>
          )}
        </div>

        <div className="card" style={{ padding: '1.5rem', marginTop: '1rem' }}>
          <h3 style={{ marginBottom: '0.5rem', fontSize: '0.9375rem', fontWeight: 600 }}>Workflow</h3>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Tickets are processed through the following pipeline:
          </p>
          <ol style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginTop: '0.5rem', paddingLeft: '1.25rem', lineHeight: 2 }}>
            <li>Input validation and guardrails</li>
            <li>Audit Agent scores ticket quality (0-100)</li>
            <li>If incomplete, Question Agent asks up to 3 clarifying questions</li>
            <li>Rewrite Agent produces a professional bug report</li>
            <li>Duplicate Agent checks ChromaDB vector index (85% threshold)</li>
            <li>If unique, MCP tool creates a GitHub issue</li>
            <li>Ticket is indexed for future duplicate detection</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
