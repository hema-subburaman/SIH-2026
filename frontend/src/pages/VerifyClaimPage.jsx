import React, { useState } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  HelpCircle, 
  Search, 
  ShieldCheck, 
  AlertCircle, 
  FileCheck,
  Sparkles,
  Info
} from 'lucide-react';
import { verifyClaim } from '../services/api';
import SourceAttribution from '../components/SourceAttribution';

export default function VerifyClaimPage({ currentCity, coordinates }) {
  const [claimInput, setClaimInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const sampleClaims = [
    `There is a cyclone warning in ${currentCity} right now`,
    `It is raining now in ${currentCity}`,
    `Tomorrow will be very hot in ${currentCity}`,
    `Wind speeds will exceed 40 km/h tomorrow`
  ];

  const handleVerify = async (textToVerify) => {
    const text = (textToVerify || claimInput).trim();
    if (!text || loading) return;

    setLoading(true);
    try {
      const res = await verifyClaim(text, currentCity, coordinates?.lat, coordinates?.lon);
      setResult(res);
    } catch (err) {
      console.error('Claim verification error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getVerdictIcon = (status) => {
    switch (status) {
      case 'VERIFIED':
        return <CheckCircle2 size={18} style={{ color: 'var(--accent-emerald)' }} />;
      case 'CONTRADICTED':
        return <XCircle size={18} style={{ color: 'var(--accent-rose)' }} />;
      default:
        return <HelpCircle size={18} style={{ color: 'var(--accent-amber)' }} />;
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileCheck size={22} style={{ color: 'var(--accent-cyan)' }} />
          <span>Meteorological Fact-Check & Claim Verification</span>
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Combat weather misinformation and social media rumors by verifying statements against live observational telemetry and official warning archives for <strong>{currentCity}</strong>.
        </p>
      </div>

      {/* Input Form */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleVerify();
          }}
          style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}
        >
          <input
            type="text"
            className="chat-input"
            placeholder={`Enter weather statement to verify (e.g. "There is a cyclone warning in ${currentCity}")...`}
            value={claimInput}
            onChange={(e) => setClaimInput(e.target.value)}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={loading || !claimInput.trim()}
          >
            <Search size={16} />
            <span>Verify Claim</span>
          </button>
        </form>

        {/* Quick Sample Claims */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Try sample claims:</span>
          {sampleClaims.map((c, idx) => (
            <button
              key={idx}
              type="button"
              className="quick-chip"
              onClick={() => {
                setClaimInput(c);
                handleVerify(c);
              }}
            >
              "{c}"
            </button>
          ))}
        </div>
      </div>

      {/* Verification Result Card */}
      {loading ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Cross-referencing sensor observations, numerical forecasts, and IMD warning bulletins...
        </div>
      ) : result ? (
        <div className="glass-panel" style={{ padding: '1.75rem', borderLeft: `5px solid ${result.status === 'VERIFIED' ? 'var(--accent-emerald)' : (result.status === 'CONTRADICTED' ? 'var(--accent-rose)' : 'var(--accent-amber)')}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span className={`verdict-badge ${result.status}`}>
                {getVerdictIcon(result.status)}
                <span>{result.status}</span>
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Confidence: <strong>{Math.round(result.confidence * 100)}%</strong>
              </span>
            </div>

            {result.official_warning_checked && (
              <span className="source-tag">
                <ShieldCheck size={12} style={{ color: 'var(--accent-cyan)' }} />
                <span>Official Warning Feeds Checked</span>
              </span>
            )}
          </div>

          <div style={{ fontSize: '1.05rem', fontWeight: 600, color: '#fff', marginBottom: '0.75rem', lineHeight: '1.4' }}>
            {result.verdict_summary}
          </div>

          {/* Evidence Checklist */}
          <div style={{ marginTop: '1rem' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
              Corroborating Telemetry & Evidence Factors:
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {result.evidence_factors.map((ev, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: '0.5rem',
                    fontSize: '0.825rem',
                    color: '#e2e8f0',
                    background: 'rgba(0,0,0,0.25)',
                    padding: '0.4rem 0.75rem',
                    borderRadius: 'var(--radius-sm)'
                  }}
                >
                  <span style={{ color: 'var(--accent-cyan)' }}>•</span>
                  <span>{ev}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Protocol Disclaimer */}
          <div style={{
            marginTop: '1.25rem',
            padding: '0.65rem 0.85rem',
            background: 'rgba(255, 255, 255, 0.02)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.5rem'
          }}>
            <Info size={15} style={{ color: 'var(--accent-amber)', flexShrink: 0, marginTop: '2px' }} />
            <div>{result.disclaimer}</div>
          </div>

          <SourceAttribution source={result.source_attribution} />
        </div>
      ) : null}
    </div>
  );
}
