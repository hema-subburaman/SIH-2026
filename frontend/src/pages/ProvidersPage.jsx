import React, { useState, useEffect } from 'react';
import { Cpu, CheckCircle2, AlertCircle, RefreshCw, Layers, ShieldCheck, Database, GitFork } from 'lucide-react';
import { fetchProvidersStatus } from '../services/api';

export default function ProvidersPage() {
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const data = await fetchProvidersStatus();
      setProviders(data.providers || []);
    } catch (err) {
      console.error('Failed to load providers status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Cpu size={22} style={{ color: 'var(--accent-indigo)' }} />
            <span>NWP Models & Provider Architecture</span>
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Transparent operational telemetry for Numerical Weather Prediction (NWP), observational feeds, and early warning systems.
          </p>
        </div>

        <button
          type="button"
          className="gps-btn"
          onClick={loadStatus}
          title="Refresh provider status"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Architecture Highlights */}
      <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem', background: 'rgba(99, 102, 241, 0.06)', border: '1px solid rgba(99, 102, 241, 0.25)' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-indigo)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.5rem' }}>
          <Layers size={16} />
          <span>Provider Abstraction Layer (SIH Section 29 Compliance)</span>
        </h3>
        <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.45' }}>
          The backend decouples ingestion through polymorphic contracts: <code style={{ color: 'var(--accent-cyan)' }}>WeatherProvider</code>, <code style={{ color: 'var(--accent-cyan)' }}>ForecastProvider</code>, <code style={{ color: 'var(--accent-cyan)' }}>WarningProvider</code>, and <code style={{ color: 'var(--accent-cyan)' }}>NWPProvider</code>.
          Unconfigured high-performance numerical prediction pipelines (GFS / WRF) explicitly report <em>"Provider not configured"</em> rather than generating fabricated model runs.
        </p>
      </div>

      {loading ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Probing provider connection status...
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '1.25rem' }}>
          {providers.map((p) => (
            <div
              key={p.id}
              className="glass-panel"
              style={{
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                borderTop: `3px solid ${p.configured ? 'var(--accent-emerald)' : 'var(--accent-amber)'}`
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div>
                    <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff' }}>{p.name}</h4>
                    <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>{p.type}</span>
                  </div>

                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.3rem',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      padding: '3px 8px',
                      borderRadius: 'var(--radius-full)',
                      background: p.configured ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: p.configured ? 'var(--accent-emerald)' : 'var(--accent-amber)',
                      border: `1px solid ${p.configured ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`
                    }}
                  >
                    {p.configured ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                    <span>{p.status}</span>
                  </span>
                </div>

                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.45', margin: '0.75rem 0' }}>
                  {p.notes}
                </p>

                {p.resolution && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Grid Resolution: <strong style={{ color: '#fff' }}>{p.resolution}</strong>
                  </div>
                )}
              </div>

              <div style={{
                marginTop: '1rem',
                paddingTop: '0.75rem',
                borderTop: '1px solid var(--border-subtle)',
                fontSize: '0.72rem',
                fontFamily: "'JetBrains Mono', monospace",
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem'
              }}>
                <Database size={12} />
                <span>Protocol: {p.id.toUpperCase()}_ADAPTER_V1</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
