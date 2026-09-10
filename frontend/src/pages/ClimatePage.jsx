import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart3, CloudRain, Thermometer, ShieldAlert, History, Calendar } from 'lucide-react';
import { fetchClimateTrends } from '../services/api';
import SourceAttribution from '../components/SourceAttribution';
import { UI_TRANSLATIONS } from '../utils/constants';

export default function ClimatePage({ currentCity, coordinates, currentLang = 'en' }) {
  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
  const [climateData, setClimateData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timespan, setTimespan] = useState(10); // 10, 15, 20 years

  useEffect(() => {
    async function loadClimate() {
      setLoading(true);
      try {
        const data = await fetchClimateTrends(currentCity, coordinates?.lat, coordinates?.lon, timespan);
        setClimateData(data);
      } catch (err) {
        console.error('Failed to load climate history:', err);
      } finally {
        setLoading(false);
      }
    }
    loadClimate();
  }, [currentCity, timespan]);

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        {t.loadingClimate ? t.loadingClimate.replace('{city}', currentCity) : `Retrieving historical meteorological reanalysis archives (ERA5 / WMO) for ${currentCity}...`}
      </div>
    );
  }

  if (!climateData || climateData.available === false || !climateData.data_points || climateData.data_points.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '0.5rem' }}>
          {t.climateUnavailableTitle || 'Historical climate data temporarily unavailable.'}
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '520px', margin: '0 auto 1rem auto' }}>
          {climateData?.message || (t.climateUnavailableDesc ? t.climateUnavailableDesc.replace('{city}', currentCity) : `Historical climate records for ${currentCity} could not be retrieved from the observational archive.`)}
        </p>
        <div style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
          {t.climateProtocol || 'Data Integrity Protocol: Zero synthetic or mathematically generated climate data.'}
        </div>
        {climateData?.source && (
          <SourceAttribution source={climateData.source} note="Verified reanalysis feed" />
        )}
      </div>
    );
  }

  const { data_points, baseline_avg_temp, recent_avg_temp, temp_change_rate, trend_summary, source, citation } = climateData;

  // Chart Dimensions
  const svgWidth = 720;
  const svgHeight = 220;
  const padX = 45;
  const padY = 35;

  const temps = data_points.map((d) => d.avg_temp);
  const minT = Math.min(...temps) - 0.5;
  const maxT = Math.max(...temps) + 0.5;
  const rangeT = maxT - minT || 1;

  const points = data_points.map((d, idx) => {
    const x = padX + (idx / Math.max(data_points.length - 1, 1)) * (svgWidth - 2 * padX);
    const y = svgHeight - padY - ((d.avg_temp - minT) / rangeT) * (svgHeight - 2 * padY);
    return { x, y, temp: d.avg_temp, year: d.year, rainfall: d.total_rainfall_mm, anomaly: d.anomaly };
  });

  const pathD = points.length > 0
    ? `M ${points[0].x} ${points[0].y} ` + points.slice(1).map((p) => `L ${p.x} ${p.y}`).join(' ')
    : '';

  const getTimespanLabel = (yr) => {
    if (yr === 10) return t.years10 || '10 Years';
    if (yr === 15) return t.years15 || '15 Years';
    if (yr === 20) return t.years20 || '20 Years';
    return `${yr} Years`;
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <TrendingUp size={22} style={{ color: 'var(--accent-cyan)' }} />
            <span>{t.climateTitle || 'Climate Trends & Historical Telemetry'}</span>
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {t.climateSubtitle || 'Long-term temperature trajectories and anomaly observations derived from ERA5 reanalysis archives'} ({currentCity}).
          </p>
        </div>

        {/* Timespan Selector */}
        <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
          {[10, 15, 20].map((yr) => (
            <button
              key={yr}
              type="button"
              className={`preset-chip ${timespan === yr ? 'active' : ''}`}
              onClick={() => setTimespan(yr)}
            >
              {getTimespanLabel(yr)}
            </button>
          ))}
        </div>
      </div>

      {/* 3 Metric Highlight Cards - Responsive Grid */}
      <div className="climate-metrics-grid">
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <History size={14} style={{ color: 'var(--accent-indigo)' }} />
            <span>{t.baselineAvg || 'Observational Baseline Mean'}</span>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#fff', margin: '4px 0' }}>
            {baseline_avg_temp.toFixed(1)}°C
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Historical benchmark
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Thermometer size={14} style={{ color: 'var(--accent-rose)' }} />
            <span>{t.recentAvg || 'Recent Decadal Mean'}</span>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--accent-rose)', margin: '4px 0' }}>
            {recent_avg_temp.toFixed(1)}°C
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Recorded mean over recent period
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <TrendingUp size={14} style={{ color: 'var(--accent-amber)' }} />
            <span>{t.warmingRate || 'Decadal Trend Rate'}</span>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: temp_change_rate >= 0 ? 'var(--accent-amber)' : 'var(--accent-emerald)', margin: '4px 0' }}>
            {temp_change_rate >= 0 ? `+${temp_change_rate}°C` : `${temp_change_rate}°C`}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Thermal shift per decade
          </div>
        </div>
      </div>

      {/* Main Historical Visualization Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>
              {t.annualMeanTemp || 'Annual Mean Temperature Curve'} ({data_points[0]?.year} - {data_points[data_points.length - 1]?.year})
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Verified observational records from global reanalysis grids.
            </p>
          </div>
        </div>

        {/* SVG Chart */}
        <div className="chart-scroll-container">
          <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: '100%', minWidth: '460px', height: '220px', display: 'block' }}>
            <defs>
              <linearGradient id="climateGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid Line */}
            <line x1={padX} y1={svgHeight - padY} x2={svgWidth - padX} y2={svgHeight - padY} stroke="rgba(255,255,255,0.1)" />
            <line x1={padX} y1={padY} x2={svgWidth - padX} y2={padY} stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />

            {/* Area Fill */}
            {points.length > 0 && (
              <path
                d={`${pathD} L ${points[points.length - 1].x} ${svgHeight - padY} L ${points[0].x} ${svgHeight - padY} Z`}
                fill="url(#climateGrad)"
              />
            )}

            {/* Line */}
            <path
              d={pathD}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2.5"
              strokeLinecap="round"
            />

            {/* Dots */}
            {points.map((p, i) => (
              <g key={i}>
                <circle cx={p.x} cy={p.y} r="4" fill="#080c16" stroke="#f59e0b" strokeWidth="2" />
                <text x={p.x} y={p.y - 8} fill="#fff" fontSize="10" fontWeight="700" textAnchor="middle">
                  {p.temp.toFixed(1)}°
                </text>
                <text x={p.x} y={svgHeight - 12} fill="var(--text-muted)" fontSize="10" textAnchor="middle">
                  {p.year}
                </text>
              </g>
            ))}
          </svg>
        </div>

        {/* Narrative Summary */}
        <div style={{
          marginTop: '1.25rem',
          padding: '0.85rem 1rem',
          background: 'rgba(255, 255, 255, 0.03)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '0.85rem',
          color: '#e2e8f0',
          lineHeight: '1.5',
          borderLeft: '3px solid var(--accent-cyan)'
        }}>
          <strong>Observational Climate Summary: </strong>
          {trend_summary}
        </div>

        <SourceAttribution source={source} note={citation} />
      </div>
    </div>
  );
}
