import React, { useState, useEffect } from 'react';
import {
  Cpu,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Layers,
  Database,
  GitCompare,
  Clock,
  Activity,
  ChevronRight,
  Info
} from 'lucide-react';
import { fetchProvidersStatus, fetchModelComparison } from '../services/api';
import { UI_TRANSLATIONS } from '../utils/constants';

export default function ProvidersPage({ currentCity = 'Chennai', currentLang = 'en' }) {
  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
  const [providers, setProviders] = useState([]);
  const [ingestion, setIngestion] = useState(null);
  const [loading, setLoading] = useState(true);

  // Model comparison state
  const [compCity, setCompCity] = useState(currentCity || 'Chennai');
  const [comparison, setComparison] = useState(null);
  const [compLoading, setCompLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('providers'); // 'providers' or 'comparison'

  const loadStatus = async () => {
    setLoading(true);
    try {
      const data = await fetchProvidersStatus();
      setProviders(data.providers || []);
      setIngestion(data.ingestion_status || null);
    } catch (err) {
      console.error('Failed to load providers status:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadComparison = async () => {
    setCompLoading(true);
    try {
      const data = await fetchModelComparison(compCity, null, null, 5);
      setComparison(data);
    } catch (err) {
      console.error('Failed to load model comparison:', err);
    } finally {
      setCompLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  useEffect(() => {
    if (activeTab === 'comparison' && !comparison) {
      loadComparison();
    }
  }, [activeTab]);

  const getStatusBadge = (status, configured) => {
    const s = (status || '').toUpperCase();
    if (s.includes('AVAILABLE') || s.includes('ACTIVE') || s.includes('OPERATIONAL')) {
      return {
        bg: 'rgba(16, 185, 129, 0.15)',
        color: 'var(--accent-emerald)',
        border: 'rgba(16, 185, 129, 0.4)',
        icon: <CheckCircle2 size={12} />,
        label: t.statusAvailable || 'AVAILABLE',
      };
    }
    if (s.includes('NOT CONFIGURED') || !configured) {
      return {
        bg: 'rgba(245, 158, 11, 0.15)',
        color: 'var(--accent-amber)',
        border: 'rgba(245, 158, 11, 0.4)',
        icon: <AlertCircle size={12} />,
        label: t.statusNotConfigured || 'NOT CONFIGURED',
      };
    }
    return {
      bg: 'rgba(239, 68, 68, 0.15)',
      color: '#f87171',
      border: 'rgba(239, 68, 68, 0.4)',
      icon: <AlertCircle size={12} />,
      label: 'UNAVAILABLE',
    };
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Cpu size={22} style={{ color: 'var(--accent-indigo)' }} />
            <span>{t.nwpTitle || 'Numerical Weather Prediction (NWP) Models & Telemetry Providers'}</span>
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {t.nwpSubtitle || 'Transparent operational status of global and regional numerical weather models, ingestion pipelines, and multi-model consensus.'}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', background: 'rgba(255, 255, 255, 0.05)', borderRadius: 'var(--radius-md)', padding: '3px' }}>
            <button
              type="button"
              className={`pill-btn ${activeTab === 'providers' ? 'active' : ''}`}
              onClick={() => setActiveTab('providers')}
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            >
              {t.tabProviders || 'Providers Telemetry'}
            </button>
            <button
              type="button"
              className={`pill-btn ${activeTab === 'comparison' ? 'active' : ''}`}
              onClick={() => setActiveTab('comparison')}
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            >
              {t.tabComparison || 'Multi-Model Consensus'}
            </button>
          </div>

          <button
            type="button"
            className="gps-btn"
            onClick={activeTab === 'providers' ? loadStatus : loadComparison}
            title={t.refreshTelemetry || 'Refresh'}
            aria-label={t.refreshTelemetry || 'Refresh'}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Tabs view */}
      {activeTab === 'providers' && (
        <>
          {/* Architecture Highlights Banner */}
          <div className="glass-panel" style={{ padding: '1.1rem 1.25rem', marginBottom: '1.5rem', background: 'rgba(99, 102, 241, 0.06)', border: '1px solid rgba(99, 102, 241, 0.25)' }}>
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--accent-indigo)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
              <Layers size={16} />
              <span>Zero-Fabrication Data Transparency Standard</span>
            </h3>
            <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.45', margin: 0 }}>
              WeatherGPT enforces strict source honesty. Unconfigured or offline models explicitly report <strong style={{ color: 'var(--accent-amber)' }}>{t.statusNotConfigured || 'NOT CONFIGURED'}</strong> or <strong style={{ color: '#f87171' }}>UNAVAILABLE</strong> rather than fabricating synthetic predictions.
            </p>
          </div>

          {/* Providers Grid */}
          {loading ? (
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Probing provider telemetry and model endpoints...
            </div>
          ) : (
            <div className="providers-cards-grid">
              {providers.map((p) => {
                const badge = getStatusBadge(p.status, p.configured);
                return (
                  <div
                    key={p.id}
                    className="glass-panel"
                    style={{
                      padding: '1.35rem',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      borderTop: `3px solid ${badge.color}`,
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem', gap: '0.5rem' }}>
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
                            background: badge.bg,
                            color: badge.color,
                            border: `1px solid ${badge.border}`,
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {badge.icon}
                          <span>{badge.label}</span>
                        </span>
                      </div>

                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.45', margin: '0.75rem 0' }}>
                        {p.notes}
                      </p>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                        <div>
                          Source: <strong style={{ color: '#e2e8f0' }}>{p.source}</strong>
                        </div>
                        {p.resolution && (
                          <div>
                            Resolution: <strong style={{ color: '#e2e8f0' }}>{p.resolution}</strong>
                          </div>
                        )}
                        {p.latest_run && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                            <Clock size={12} />
                            <span>Cycle / Run: <strong style={{ color: '#e2e8f0' }}>{p.latest_run}</strong></span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div style={{
                      marginTop: '1rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid var(--border-subtle)',
                      fontSize: '0.72rem',
                      fontFamily: "'JetBrains Mono', monospace",
                      color: 'var(--text-muted)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '0.35rem'
                    }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <Database size={12} />
                        <span>{p.is_official ? 'OFFICIAL_GOV_FEED' : 'NUMERICAL_MODEL'}</span>
                      </span>
                      {p.last_updated && (
                        <span>Synced: {new Date(p.last_updated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Ingestion Pipeline Status Panel */}
          {ingestion && ingestion.jobs && Object.keys(ingestion.jobs).length > 0 && (
            <div className="glass-panel" style={{ marginTop: '1.75rem', padding: '1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#fff' }}>
                  <Activity size={16} style={{ color: 'var(--accent-cyan)' }} />
                  <span>{t.pipelineHealth || 'Meteorological Ingestion Worker Status'}</span>
                </h4>
                {ingestion.last_run && (
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Last Run: {new Date(ingestion.last_run).toLocaleTimeString()}
                  </span>
                )}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                {Object.entries(ingestion.jobs).map(([key, j]) => (
                  <div key={key} style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#e2e8f0' }}>{j.job_name}</span>
                      <span style={{ fontSize: '0.7rem', color: j.success ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
                        {j.success ? 'OK' : 'HALTED'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      Execution: {j.execution_time_ms}ms | Records: {j.records_ingested}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Multi-Model Comparison Tab */}
      {activeTab === 'comparison' && (
        <div>
          {/* Comparison Search Input */}
          <div className="glass-panel" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem', display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              {t.targetCity || 'Target City:'}
            </span>
            <input
              type="text"
              className="chat-input"
              style={{ width: 'min(240px, 100%)', flex: '1 1 180px', padding: '0.45rem 0.75rem', fontSize: '0.85rem' }}
              value={compCity}
              onChange={(e) => setCompCity(e.target.value)}
              placeholder="e.g., Chennai, Delhi, Mumbai"
            />
            <button
              type="button"
              className="pill-btn active"
              onClick={loadComparison}
              disabled={compLoading}
              style={{ padding: '6px 14px', fontSize: '0.82rem' }}
            >
              {compLoading ? (t.loading || 'Comparing...') : (t.compareModels || 'Compare Forecast Models')}
            </button>
          </div>

          {compLoading ? (
            <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              {t.comparingModels || 'Executing multi-model normalization and agreement analysis...'}
            </div>
          ) : comparison ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Consensus Overview Card */}
              <div className="glass-panel" style={{ padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
                  <div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <GitCompare size={18} style={{ color: 'var(--accent-indigo)' }} />
                      <span>{t.consensusFor ? t.consensusFor.replace('{city}', comparison.location?.name) : `Consensus for ${comparison.location?.name}`}</span>
                    </h3>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Models Evaluated: <strong>{comparison.models_available_count}/{comparison.models_total} Available</strong>
                      {' '}({comparison.models_available?.join(', ') || 'None'})
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    {comparison.agreement_score !== null && (
                      <div style={{ background: 'rgba(99, 102, 241, 0.15)', border: '1px solid rgba(99, 102, 241, 0.4)', borderRadius: 'var(--radius-md)', padding: '4px 10px', fontSize: '0.78rem' }}>
                        {t.modelAgreementScore || 'Agreement'}: <strong style={{ color: 'var(--accent-indigo)' }}>{Math.round(comparison.agreement_score * 100)}%</strong>
                      </div>
                    )}
                    <div style={{
                      background: comparison.confidence === 'High' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: comparison.confidence === 'High' ? 'var(--accent-emerald)' : 'var(--accent-amber)',
                      border: `1px solid ${comparison.confidence === 'High' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
                      borderRadius: 'var(--radius-md)',
                      padding: '4px 10px',
                      fontSize: '0.78rem',
                      fontWeight: 700
                    }}>
                      Confidence: {comparison.confidence}
                    </div>
                  </div>
                </div>

                <p style={{ fontSize: '0.85rem', color: '#e2e8f0', lineHeight: '1.5', margin: '0.5rem 0' }}>
                  {comparison.summary}
                </p>

                {comparison.disagreements?.length > 0 && (
                  <div style={{ marginTop: '0.75rem', padding: '0.65rem 0.9rem', background: 'rgba(245, 158, 11, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-amber)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.3rem' }}>
                      <AlertCircle size={13} />
                      <span>{t.divergenceAnalysis || 'Model Disagreement Signals'}</span>
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.75rem', color: '#cbd5e1' }}>
                      {comparison.disagreements.map((dis, idx) => (
                        <li key={idx}>{dis}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* Consensus Daily Matrix Table */}
              {comparison.consensus_daily?.length > 0 && (
                <div className="glass-panel" style={{ padding: '1.25rem', overflowX: 'auto' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.75rem', color: '#fff' }}>
                    {t.consensusMatrix || 'Forecast Consensus Matrix (Multi-Model)'}
                  </h4>
                  <div className="responsive-table-container">
                    <table style={{ width: '100%', minWidth: '550px', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                          <th style={{ padding: '8px 10px' }}>Date</th>
                          <th style={{ padding: '8px 10px' }}>Consensus Temp</th>
                          <th style={{ padding: '8px 10px' }}>Spread</th>
                          <th style={{ padding: '8px 10px' }}>Rain Probability</th>
                          <th style={{ padding: '8px 10px' }}>Consensus Condition</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparison.consensus_daily.map((cd, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                            <td style={{ padding: '8px 10px', fontWeight: 600, color: '#e2e8f0' }}>{cd.date}</td>
                            <td style={{ padding: '8px 10px', color: '#fff' }}>{cd.mean_temp !== null ? `${cd.mean_temp}°C` : 'N/A'}</td>
                            <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>±{cd.temp_spread}</td>
                            <td style={{ padding: '8px 10px', color: cd.mean_pop >= 0.4 ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>
                              {cd.mean_pop !== null ? `${Math.round(cd.mean_pop * 100)}%` : 'N/A'}
                            </td>
                            <td style={{ padding: '8px 10px', color: 'var(--accent-cyan)' }}>{cd.condition_consensus}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
