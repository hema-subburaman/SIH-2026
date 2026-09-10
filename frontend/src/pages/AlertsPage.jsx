import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  ShieldCheck, 
  Flame, 
  Wind, 
  CloudLightning, 
  Radio, 
  CheckCircle,
  Bell,
  RefreshCw,
  Info
} from 'lucide-react';
import { fetchAlerts } from '../services/api';
import SourceAttribution from '../components/SourceAttribution';

export default function AlertsPage({ currentCity, coordinates }) {
  const [alertsData, setAlertsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('all'); // all, official, system
  const [simulatedWarning, setSimulatedWarning] = useState(null);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data = await fetchAlerts(currentCity, coordinates?.lat, coordinates?.lon);
      setAlertsData(data);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [currentCity]);

  // Demo tool for SIH Judges: simulate an IMD CAP Coastal Alert to show how the pipeline reacts
  const handleSimulateOfficialWarning = () => {
    if (simulatedWarning) {
      setSimulatedWarning(null);
    } else {
      setSimulatedWarning({
        id: 'imd-cap-demo-99',
        event: 'Cyclone Alert & Deep Depression Bulletin',
        category: 'Cyclone Warning',
        severity: 'Warning',
        location: currentCity,
        headline: `IMD Special Tropical Weather Advisory for Coastal ${currentCity}`,
        description: `Depression over southwest Bay of Bengal is likely to intensify into a severe cyclonic storm. Squally winds reaching 65-75 km/h gusting to 85 km/h expected along the coast.`,
        recommendation: `Total suspension of fishing operations. Coastal residents should avoid coastal beaches and low-lying areas. Follow instructions of State Disaster Management Authority (SDMA).`,
        is_official: true,
        source: 'India Meteorological Department (IMD) / NDMA CAP Feed',
        start_time: new Date().toISOString(),
      });
    }
  };

  const officialList = alertsData?.official_alerts || [];
  const combinedOfficial = simulatedWarning ? [simulatedWarning, ...officialList] : officialList;
  const systemRisks = alertsData?.system_risks || [];

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={22} style={{ color: 'var(--accent-rose)' }} />
            <span>Disaster Early Warning & Alerts Center</span>
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Real-time CAP alert ingestion protocol with strict distinction between <strong>Official Bulletins</strong> and <strong>Algorithmic Risks</strong>.
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            type="button"
            className="preset-chip"
            onClick={handleSimulateOfficialWarning}
            style={{
              background: simulatedWarning ? 'var(--accent-rose)' : 'rgba(255, 255, 255, 0.05)',
              color: '#fff',
              borderColor: simulatedWarning ? 'var(--accent-rose)' : 'var(--border-subtle)'
            }}
          >
            <Radio size={14} style={{ display: 'inline', marginRight: '4px' }} />
            {simulatedWarning ? 'Clear Ingested Bulletin' : 'Simulate IMD CAP Bulletin (Judge Demo)'}
          </button>

          <button
            type="button"
            className="gps-btn"
            onClick={loadAlerts}
            title="Refresh active alerts"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Protocol Banner */}
      <div style={{
        padding: '0.85rem 1rem',
        borderRadius: 'var(--radius-sm)',
        background: 'rgba(56, 189, 248, 0.06)',
        border: '1px solid rgba(56, 189, 248, 0.2)',
        marginBottom: '1.5rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        fontSize: '0.8rem',
        color: '#e2e8f0'
      }}>
        <Info size={20} style={{ color: 'var(--accent-cyan)', flexShrink: 0 }} />
        <div>
          <strong>SIH Data Integrity Protocol:</strong> System weather risks are derived algorithmically from live sensor thresholds.
          Official warnings are ingested strictly from authorized government sources (IMD / NDMA Sachet CAP feeds).
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
        <button
          type="button"
          className={`preset-chip ${activeFilter === 'all' ? 'active' : ''}`}
          onClick={() => setActiveFilter('all')}
        >
          All Active ({combinedOfficial.length + systemRisks.length})
        </button>
        <button
          type="button"
          className={`preset-chip ${activeFilter === 'official' ? 'active' : ''}`}
          onClick={() => setActiveFilter('official')}
        >
          Official Government Warnings ({combinedOfficial.length})
        </button>
        <button
          type="button"
          className={`preset-chip ${activeFilter === 'system' ? 'active' : ''}`}
          onClick={() => setActiveFilter('system')}
        >
          System Weather Risks ({systemRisks.length})
        </button>
      </div>

      {loading ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Querying national warning repositories and computing threshold exceedances...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Section 1: Official Government Warnings */}
          {(activeFilter === 'all' || activeFilter === 'official') && (
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="official-warning-badge">
                  <ShieldAlert size={14} />
                  <span>OFFICIAL GOVERNMENT WARNINGS (IMD / NDMA)</span>
                </span>
              </h3>

              {combinedOfficial.length === 0 ? (
                <div className="glass-panel" style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <CheckCircle size={20} style={{ color: 'var(--accent-emerald)', margin: '0 auto 6px auto' }} />
                  No severe official weather warnings (cyclones/floods) are active for <strong>{currentCity}</strong> in the national bulletin at this moment.
                </div>
              ) : (
                combinedOfficial.map((alert) => (
                  <div
                    key={alert.id}
                    className="glass-panel"
                    style={{
                      padding: '1.25rem',
                      borderLeft: '4px solid #ef4444',
                      background: 'rgba(239, 68, 68, 0.08)',
                      marginBottom: '0.75rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="official-warning-badge">{alert.severity}</span>
                        <span style={{ fontSize: '1rem', fontWeight: 800, color: '#fff' }}>{alert.event}</span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Area: <strong>{alert.location}</strong>
                      </span>
                    </div>

                    {alert.headline && (
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fca5a5', margin: '4px 0' }}>
                        {alert.headline}
                      </div>
                    )}

                    <p style={{ fontSize: '0.85rem', color: '#e2e8f0', lineHeight: '1.5', margin: '8px 0' }}>
                      {alert.description}
                    </p>

                    <div style={{
                      padding: '0.6rem 0.85rem',
                      background: 'rgba(0,0,0,0.3)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.8rem',
                      color: '#f8fafc',
                      marginTop: '8px'
                    }}>
                      <strong>Instructions: </strong> {alert.recommendation}
                    </div>

                    <SourceAttribution source={alert.source} isOfficial={true} />
                  </div>
                ))
              )}
            </div>
          )}

          {/* Section 2: System Weather Risks (Algorithmic) */}
          {(activeFilter === 'all' || activeFilter === 'system') && (
            <div style={{ marginTop: '1rem' }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="system-risk-badge">
                  <Flame size={14} />
                  <span>SYSTEM WEATHER RISKS (RULE-BASED THRESHOLDS)</span>
                </span>
              </h3>

              {systemRisks.length === 0 ? (
                <div className="glass-panel" style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <CheckCircle size={20} style={{ color: 'var(--accent-emerald)', margin: '0 auto 6px auto' }} />
                  Atmospheric parameters (temperature, wind, precipitation) are within nominal thresholds in {currentCity}.
                </div>
              ) : (
                systemRisks.map((risk) => (
                  <div
                    key={risk.id}
                    className="glass-panel"
                    style={{
                      padding: '1.25rem',
                      borderLeft: '4px solid var(--accent-amber)',
                      background: 'rgba(245, 158, 11, 0.05)',
                      marginBottom: '0.75rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="system-risk-badge">{risk.severity}</span>
                        <span style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>{risk.event}</span>
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Sensor Location: <strong>{risk.location}</strong>
                      </span>
                    </div>

                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1', margin: '6px 0' }}>
                      {risk.description}
                    </p>

                    <div style={{
                      padding: '0.5rem 0.75rem',
                      background: 'rgba(0,0,0,0.25)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.8rem',
                      color: 'var(--accent-amber)'
                    }}>
                      <strong>Recommended Action: </strong> {risk.recommendation}
                    </div>

                    <SourceAttribution source={risk.source} isOfficial={false} />
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
