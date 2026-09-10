import React from 'react';
import { Database, ShieldCheck } from 'lucide-react';

export default function SourceAttribution({ source, note, isOfficial = false }) {
  if (!source) return null;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      fontSize: '0.72rem',
      color: 'var(--text-muted)',
      paddingTop: '0.75rem',
      marginTop: '0.75rem',
      borderTop: '1px solid var(--border-subtle)',
      fontFamily: "'JetBrains Mono', monospace"
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        {isOfficial ? (
          <ShieldCheck size={13} style={{ color: 'var(--accent-rose)' }} />
        ) : (
          <Database size={13} style={{ color: 'var(--accent-cyan)' }} />
        )}
        <span><strong>Source:</strong> {source}</span>
      </div>
      {note && <span style={{ fontStyle: 'italic' }}>{note}</span>}
    </div>
  );
}
