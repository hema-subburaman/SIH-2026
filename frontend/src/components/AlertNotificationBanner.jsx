import React, { useState, useEffect } from 'react';
import { ShieldAlert, X, Bell, BellOff, ExternalLink } from 'lucide-react';

export default function AlertNotificationBanner({ incomingAlert, onDismiss }) {
  const [notificationPermission, setNotificationPermission] = useState('default');
  const [hasPrompted, setHasPrompted] = useState(false);

  useEffect(() => {
    if ('Notification' in window) {
      setNotificationPermission(Notification.permission);
    }
  }, []);

  // When a new incoming official alert arrives, show a browser notification if permitted
  useEffect(() => {
    if (!incomingAlert || !incomingAlert.is_official) return;

    if ('Notification' in window && Notification.permission === 'granted') {
      try {
        const title = "OFFICIAL WEATHER WARNING";
        const body = `${incomingAlert.event || 'Emergency Warning'} — ${incomingAlert.location || 'Your Area'}\nSource: ${incomingAlert.source || 'IMD / NDMA'}`;
        new Notification(title, {
          body,
          icon: '/favicon.ico',
          tag: incomingAlert.id || 'official-alert',
          renotify: false,
        });
      } catch (err) {
        console.warn('Browser notification error:', err);
      }
    }
  }, [incomingAlert]);

  const handleRequestPermission = async () => {
    if (!('Notification' in window)) {
      alert('Browser notifications are not supported on this device.');
      return;
    }

    try {
      const permission = await Notification.requestPermission();
      setNotificationPermission(permission);
      setHasPrompted(true);
    } catch (err) {
      console.warn('Permission request error:', err);
    }
  };

  if (!incomingAlert) {
    // Optionally display notification toggle chip if permission is default
    return null;
  }

  return (
    <div
      style={{
        margin: '0 0 1rem 0',
        padding: '0.85rem 1.25rem',
        borderRadius: 'var(--radius-md)',
        background: 'rgba(239, 68, 68, 0.15)',
        border: '1px solid rgba(239, 68, 68, 0.4)',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(239, 68, 68, 0.2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.75rem',
        animation: 'fadeIn 0.3s ease-in-out',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
        <div
          style={{
            padding: '6px',
            borderRadius: '50%',
            background: 'rgba(239, 68, 68, 0.25)',
            color: '#f87171',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <ShieldAlert size={20} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '0.7rem',
                fontWeight: 800,
                textTransform: 'uppercase',
                padding: '2px 6px',
                borderRadius: '4px',
                background: '#ef4444',
                color: '#fff',
                letterSpacing: '0.5px',
              }}
            >
              OFFICIAL GOVERNMENT WARNING
            </span>
            <span style={{ fontSize: '0.9rem', fontWeight: 800, color: '#fff' }}>
              {incomingAlert.event}
            </span>
            <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
              ({incomingAlert.location})
            </span>
          </div>
          <p style={{ fontSize: '0.8rem', color: '#fca5a5', margin: '3px 0 0 0', lineHeight: 1.4 }}>
            {incomingAlert.headline || incomingAlert.description}
          </p>
          <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '2px' }}>
            Source: <strong>{incomingAlert.source || 'IMD / NDMA Sachet'}</strong>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
        {'Notification' in window && notificationPermission !== 'granted' && (
          <button
            type="button"
            className="preset-chip"
            onClick={handleRequestPermission}
            title="Enable browser push notifications for emergency warnings"
            style={{
              background: 'rgba(255, 255, 255, 0.08)',
              borderColor: 'rgba(255, 255, 255, 0.2)',
              color: '#fff',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
            }}
          >
            <Bell size={13} />
            <span>Enable Alerts</span>
          </button>
        )}

        <button
          type="button"
          onClick={onDismiss}
          style={{
            background: 'none',
            border: 'none',
            color: '#cbd5e1',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '4px',
          }}
          title="Dismiss notification"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
