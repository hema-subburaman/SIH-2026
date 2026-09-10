import React from 'react';
import { 
  MapPin, 
  Wind, 
  Droplets, 
  Eye, 
  Gauge, 
  Sunrise, 
  Sunset, 
  CloudSun, 
  Compass,
  Cpu,
  Sparkles
} from 'lucide-react';
import RiskBadge from './RiskBadge';
import ExplainableFactors from './ExplainableFactors';
import SourceAttribution from './SourceAttribution';
import { UI_TRANSLATIONS, getLocalizedActivity } from '../utils/constants';

export default function CurrentWeatherCard({ weatherData, riskData, language = 'en', onOpenWhatIf }) {
  const t = UI_TRANSLATIONS[language] || UI_TRANSLATIONS.en;

  if (!weatherData || !weatherData.current) {
    return (
      <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        {t.loading || 'Loading real-time meteorological observations...'}
      </div>
    );
  }

  const { location, current, source } = weatherData;
  const locActivity = riskData?.activity ? getLocalizedActivity(riskData.activity, language) : null;

  return (
    <div className="weather-hero">
      {/* Real-Time Observation Card */}
      <div className="glass-panel hero-current-card">
        <div className="hero-badge-row">
          <div className="location-badge">
            <MapPin size={20} style={{ color: 'var(--accent-cyan)' }} />
            <span>{location.name}</span>
            {location.state && <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>, {location.state}</span>}
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span className="source-tag">
              <Sparkles size={11} style={{ color: 'var(--accent-cyan)' }} />
              <span>{t.sourceTelemetry || 'Live Meteorological Telemetry'}</span>
            </span>
          </div>
        </div>

        <div className="temp-huge-row">
          <div className="temp-huge">{Math.round(current.temperature)}°C</div>
          <div>
            <div className="weather-condition-desc">{current.condition}</div>
            <div className="weather-feels">
              {t.feelsLike} <strong>{Math.round(current.feels_like)}°C</strong>
            </div>
          </div>
        </div>

        {/* 4 Essential Metrics */}
        <div className="metrics-strip">
          <div className="metric-cell">
            <span className="metric-label">
              <Droplets size={14} style={{ color: 'var(--accent-cyan)' }} />
              {t.humidity}
            </span>
            <span className="metric-val">{current.humidity}%</span>
          </div>

          <div className="metric-cell">
            <span className="metric-label">
              <Wind size={14} style={{ color: 'var(--accent-indigo)' }} />
              {t.wind}
            </span>
            <span className="metric-val">{current.wind_speed} m/s</span>
          </div>

          <div className="metric-cell">
            <span className="metric-label">
              <Eye size={14} style={{ color: 'var(--accent-emerald)' }} />
              {t.visibility}
            </span>
            <span className="metric-val">{current.visibility ? `${(current.visibility / 1000).toFixed(1)} km` : '10 km'}</span>
          </div>

          <div className="metric-cell">
            <span className="metric-label">
              <Gauge size={14} style={{ color: 'var(--accent-amber)' }} />
              {t.pressure}
            </span>
            <span className="metric-val">{Math.round(current.pressure || 1013)} hPa</span>
          </div>
        </div>

        {/* Sun Times */}
        {(current.sunrise || current.sunset) && (
          <div style={{
            display: 'flex',
            gap: '1rem',
            flexWrap: 'wrap',
            marginTop: '0.85rem',
            fontSize: '0.8rem',
            color: 'var(--text-secondary)'
          }}>
            {current.sunrise && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Sunrise size={15} style={{ color: 'var(--accent-amber)' }} />
                {t.sunrise}: <strong>{current.sunrise}</strong>
              </span>
            )}
            {current.sunset && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Sunset size={15} style={{ color: 'var(--accent-rose)' }} />
                {t.sunset}: <strong>{current.sunset}</strong>
              </span>
            )}
          </div>
        )}

        <SourceAttribution source={source} note={weatherData.attribution_notes} />
      </div>

      {/* Weather Impact Intelligence Engine Card */}
      <div className="glass-panel hero-intelligence-card">
        <div>
          <div className="intel-header">
            <div className="intel-title">
              <Cpu size={18} style={{ color: 'var(--accent-cyan)' }} />
              <span>Weather Impact Intelligence</span>
            </div>
            {riskData && <RiskBadge level={riskData.risk_level} score={riskData.score} />}
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Activity Profile: <strong style={{ color: '#fff' }}>{locActivity?.label || riskData?.activity?.replace('_', ' ') || 'General Outdoor'}</strong>
          </div>

          {riskData ? (
            <ExplainableFactors
              factors={riskData.factors}
              explanation={riskData.explanation}
              recommendation={riskData.recommendation}
            />
          ) : (
            <div style={{ padding: '1rem', color: 'var(--text-muted)', fontSize: '0.825rem' }}>
              {t.evaluatingRisk || 'Calculating activity-specific decision support...'}
            </div>
          )}
        </div>

        {onOpenWhatIf && (
          <button
            onClick={onOpenWhatIf}
            style={{
              marginTop: '1rem',
              background: 'rgba(56, 189, 248, 0.1)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              color: 'var(--accent-cyan)',
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.4rem',
              fontFamily: 'inherit'
            }}
          >
            <span>{t.viewWhatIfAnalysis || 'Simulate Operational Impact (What-If) →'}</span>
          </button>
        )}
      </div>
    </div>
  );
}
