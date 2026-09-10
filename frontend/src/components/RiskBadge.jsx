import React from 'react';
import { ShieldCheck, AlertTriangle, AlertOctagon } from 'lucide-react';

export default function RiskBadge({ level = 'LOW', score = null }) {
  const lvl = (level || 'LOW').toUpperCase();

  const config = {
    LOW: {
      className: 'risk-badge low',
      icon: <ShieldCheck size={14} />,
      label: 'LOW RISK'
    },
    MEDIUM: {
      className: 'risk-badge medium',
      icon: <AlertTriangle size={14} />,
      label: 'MEDIUM RISK'
    },
    HIGH: {
      className: 'risk-badge high',
      icon: <AlertOctagon size={14} />,
      label: 'HIGH RISK'
    }
  };

  const current = config[lvl] || config.LOW;

  return (
    <span className={current.className}>
      {current.icon}
      <span>{current.label}</span>
      {score !== null && (
        <span style={{
          marginLeft: '4px',
          opacity: 0.8,
          fontSize: '0.7rem'
        }}>
          ({score}/100)
        </span>
      )}
    </span>
  );
}
