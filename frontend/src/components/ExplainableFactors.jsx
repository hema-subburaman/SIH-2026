import React from 'react';
import { Info, CheckCircle, AlertCircle } from 'lucide-react';

export default function ExplainableFactors({ factors = [], explanation, recommendation }) {
  if (!factors || factors.length === 0) return null;

  return (
    <div style={{ marginTop: '0.75rem' }}>
      {/* Factors List */}
      <div className="factors-list">
        {factors.map((f, idx) => {
          const sev = (f.severity || 'low').toLowerCase();
          return (
            <div key={idx} className={`factor-item ${sev}`}>
              <div className="factor-name">
                <span>{f.parameter}</span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent-cyan)' }}>
                  {f.value}
                </span>
              </div>
              <div className="factor-impact">{f.impact}</div>
            </div>
          );
        })}
      </div>

      {/* Synthesis Explanation */}
      {explanation && (
        <div style={{
          fontSize: '0.825rem',
          color: 'var(--text-secondary)',
          lineHeight: '1.45',
          margin: '0.75rem 0',
          padding: '0.5rem 0.75rem',
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: 'var(--radius-sm)',
          borderLeft: '2px solid var(--accent-indigo)'
        }}>
          <strong>Why? </strong> {explanation}
        </div>
      )}

      {/* Actionable Recommendation */}
      {recommendation && (
        <div className="recommendation-box">
          <div style={{ fontWeight: '700', marginBottom: '4px', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <CheckCircle size={15} />
            <span>Actionable Advisory</span>
          </div>
          <div>{recommendation}</div>
        </div>
      )}
    </div>
  );
}
