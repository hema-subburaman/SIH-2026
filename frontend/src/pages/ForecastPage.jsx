import React, { useState, useEffect } from 'react';
import { 
  Calendar, 
  Droplets, 
  Wind, 
  CloudRain, 
  Sun, 
  Sunrise, 
  Sunset, 
  Moon, 
  Clock, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle,
  Compass,
  Layers
} from 'lucide-react';
import SourceAttribution from '../components/SourceAttribution';
import { fetchDetailedForecast } from '../services/api';

export default function ForecastPage({ forecastData, currentCity, coordinates }) {
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [detailedData, setDetailedData] = useState(null);
  const [loadingDetailed, setLoadingDetailed] = useState(false);

  // Fetch structured daily and day-part forecast
  useEffect(() => {
    async function loadDetailed() {
      setLoadingDetailed(true);
      try {
        const data = await fetchDetailedForecast(currentCity, coordinates?.lat, coordinates?.lon, 7);
        setDetailedData(data);
      } catch (e) {
        console.warn('Detailed forecast fallback:', e);
      } finally {
        setLoadingDetailed(false);
      }
    }
    loadDetailed();
  }, [currentCity, coordinates?.lat, coordinates?.lon]);

  if (!forecastData || !forecastData.forecast || forecastData.forecast.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Loading high-resolution numerical forecast data for {currentCity}...
      </div>
    );
  }

  const { forecast, source, attribution_notes } = forecastData;

  // Group 3-hourly forecast items by date (e.g. YYYY-MM-DD)
  const groupedDays = forecast.reduce((acc, item) => {
    const dateStr = item.time.split(' ')[0] || item.time.split('T')[0];
    if (!acc[dateStr]) acc[dateStr] = [];
    acc[dateStr].push(item);
    return acc;
  }, {});

  const dayKeys = Object.keys(groupedDays);

  const formatDayName = (dateStr) => {
    const date = new Date(dateStr);
    const today = new Date();
    if (date.toDateString() === today.toDateString()) return 'Today';
    
    const tomorrow = new Date();
    tomorrow.setDate(today.getDate() + 1);
    if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow';

    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const activeDayKey = dayKeys[selectedDayIndex] || dayKeys[0];
  const activeDayItems = groupedDays[activeDayKey] || [];
  const selectedSummary = detailedData?.days?.[selectedDayIndex] || null;

  // Calculate SVG line curve points for active day
  const temps = activeDayItems.map(i => i.temperature);
  const minTemp = Math.min(...temps, 20);
  const maxTemp = Math.max(...temps, 35);
  const tempRange = Math.max(maxTemp - minTemp, 1);

  const svgWidth = 700;
  const svgHeight = 160;
  const paddingX = 40;
  const paddingY = 30;

  const points = activeDayItems.map((item, idx) => {
    const x = paddingX + (idx / Math.max(activeDayItems.length - 1, 1)) * (svgWidth - 2 * paddingX);
    const y = svgHeight - paddingY - ((item.temperature - minTemp) / tempRange) * (svgHeight - 2 * paddingY);
    return { x, y, temp: item.temperature, time: item.time.split(' ')[1]?.slice(0, 5) || item.time.split('T')[1]?.slice(0, 5) || '' };
  });

  const pathD = points.length > 0 
    ? `M ${points[0].x} ${points[0].y} ` + points.slice(1).map(p => `L ${p.x} ${p.y}`).join(' ')
    : '';

  const getDayPartIcon = (part) => {
    switch (part) {
      case 'morning': return <Sunrise size={18} style={{ color: 'var(--accent-amber)' }} />;
      case 'afternoon': return <Sun size={18} style={{ color: 'var(--accent-cyan)' }} />;
      case 'evening': return <Sunset size={18} style={{ color: 'var(--accent-rose)' }} />;
      case 'night': return <Moon size={18} style={{ color: 'var(--accent-indigo)' }} />;
      default: return <Sun size={18} />;
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Numerical Weather Forecast</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            High-resolution multi-day predictions and precipitation probabilities for <strong>{currentCity}</strong>.
          </p>
        </div>
      </div>

      {/* Weekend Outlook Highlight Banner if available */}
      {detailedData?.weekend?.available && (
        <div className="glass-panel" style={{
          padding: '1rem 1.25rem',
          marginBottom: '1.5rem',
          background: 'rgba(56, 189, 248, 0.05)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
              <Calendar size={16} />
              <span>Weekend Weather Outlook</span>
            </div>
            <div style={{ fontSize: '0.85rem', color: '#e2e8f0', marginTop: '2px' }}>
              {detailedData.weekend.weekend_verdict}
            </div>
          </div>
          <div style={{
            padding: '0.4rem 0.75rem',
            background: 'rgba(0,0,0,0.3)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            whiteSpace: 'nowrap'
          }}>
            {detailedData.weekend.outdoor_recommendation}
          </div>
        </div>
      )}

      {/* Daily Overview Cards Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${Math.min(dayKeys.length, 7)}, 1fr)`,
        gap: '0.75rem',
        marginBottom: '1.5rem',
        overflowX: 'auto'
      }}>
        {dayKeys.map((dayKey, idx) => {
          const items = groupedDays[dayKey];
          const maxT = Math.max(...items.map(i => i.temperature_max || i.temperature));
          const minT = Math.min(...items.map(i => i.temperature_min || i.temperature));
          const maxPop = Math.max(...items.map(i => i.pop || 0));
          const mainCondition = items[Math.floor(items.length / 2)]?.condition || 'Clear';
          const summary = detailedData?.days?.[idx];

          return (
            <div
              key={dayKey}
              onClick={() => setSelectedDayIndex(idx)}
              className="glass-panel"
              style={{
                padding: '1rem 0.85rem',
                cursor: 'pointer',
                textAlign: 'center',
                borderColor: selectedDayIndex === idx ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                background: selectedDayIndex === idx ? 'rgba(56, 189, 248, 0.12)' : 'var(--bg-card)',
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: selectedDayIndex === idx ? 'var(--accent-cyan)' : '#fff' }}>
                {formatDayName(dayKey)}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: '4px 0 8px 0' }}>
                {dayKey}
              </div>

              <div style={{ fontSize: '1.15rem', fontWeight: 800, margin: '6px 0' }}>
                {Math.round(maxT)}° <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 400 }}>{Math.round(minT)}°</span>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '8px', minHeight: '32px' }}>
                {mainCondition}
              </div>

              {/* Rain chance pill */}
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontSize: '0.7rem',
                padding: '2px 6px',
                borderRadius: 'var(--radius-full)',
                background: maxPop >= 0.4 ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255,255,255,0.05)',
                color: maxPop >= 0.4 ? 'var(--accent-cyan)' : 'var(--text-muted)'
              }}>
                <CloudRain size={12} />
                <span>{Math.round(maxPop * 100)}%</span>
              </div>

              {/* Event Suitability Pill if available */}
              {summary && (
                <div style={{
                  marginTop: '6px',
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  color: summary.event_suitability_score >= 70 ? 'var(--accent-emerald)' : (summary.event_suitability_score >= 45 ? 'var(--accent-amber)' : 'var(--accent-rose)')
                }}>
                  {summary.event_suitability_label}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Time-of-Day Slicing (Morning, Afternoon, Evening, Night) for Selected Day */}
      {selectedSummary && selectedSummary.parts && selectedSummary.parts.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Layers size={16} style={{ color: 'var(--accent-cyan)' }} />
            <span>Time-of-Day Breakdown ({formatDayName(activeDayKey)})</span>
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
            {selectedSummary.parts.map((p, pIdx) => (
              <div
                key={pIdx}
                className="glass-panel"
                style={{ padding: '1rem', background: 'rgba(0,0,0,0.3)' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {getDayPartIcon(p.part)}
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#fff', textTransform: 'capitalize' }}>
                      {p.part}
                    </span>
                  </div>
                  <span style={{ fontSize: '1.15rem', fontWeight: 800 }}>
                    {Math.round(p.temperature)}°C
                  </span>
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)', marginBottom: '6px' }}>
                  {p.condition}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  <span>💧 {p.humidity}%</span>
                  <span>💨 {p.wind_speed} m/s</span>
                  <span style={{ color: p.pop >= 0.35 ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                    🌧️ {Math.round(p.pop * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Outdoor Event Feasibility Card for Selected Day */}
      {selectedSummary && (
        <div className="glass-panel" style={{
          padding: '1.25rem',
          marginBottom: '1.5rem',
          borderLeft: `4px solid ${selectedSummary.event_suitability_score >= 70 ? 'var(--accent-emerald)' : (selectedSummary.event_suitability_score >= 45 ? 'var(--accent-amber)' : 'var(--accent-rose)')}`
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fff' }}>
                Outdoor Event Suitability ({formatDayName(activeDayKey)})
              </span>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 'var(--radius-full)',
                background: selectedSummary.event_suitability_score >= 70 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                color: selectedSummary.event_suitability_score >= 70 ? 'var(--accent-emerald)' : 'var(--accent-amber)',
              }}>
                {selectedSummary.event_suitability_label} ({selectedSummary.event_suitability_score}/100)
              </span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Total Predicted Rain: <strong>{selectedSummary.total_rain_mm} mm</strong>
            </span>
          </div>

          <p style={{ fontSize: '0.85rem', color: '#cbd5e1', lineHeight: '1.45' }}>
            {selectedSummary.event_suitability_reason}
          </p>
        </div>
      )}

      {/* Hourly Detail Chart for Selected Day */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Clock size={16} style={{ color: 'var(--accent-cyan)' }} />
              <span>Hourly Temperature & Precipitation Timeline ({formatDayName(activeDayKey)})</span>
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Detailed 3-hour forecast intervals showing ambient temperatures and precipitation risk.
            </p>
          </div>
        </div>

        {/* SVG Curve Chart */}
        <div style={{ width: '100%', overflowX: 'auto' }}>
          <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: '100%', minWidth: '600px', height: '180px' }}>
            <defs>
              <linearGradient id="tempGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid Lines */}
            <line x1={paddingX} y1={svgHeight - paddingY} x2={svgWidth - paddingX} y2={svgHeight - paddingY} stroke="rgba(255,255,255,0.1)" />
            <line x1={paddingX} y1={paddingY} x2={svgWidth - paddingX} y2={paddingY} stroke="rgba(255,255,255,0.05)" strokeDasharray="4 4" />

            {/* Area Fill */}
            {points.length > 0 && (
              <path
                d={`${pathD} L ${points[points.length - 1].x} ${svgHeight - paddingY} L ${points[0].x} ${svgHeight - paddingY} Z`}
                fill="url(#tempGradient)"
              />
            )}

            {/* Line Path */}
            <path
              d={pathD}
              fill="none"
              stroke="#38bdf8"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Data Points */}
            {points.map((p, i) => (
              <g key={i}>
                <circle cx={p.x} cy={p.y} r="4" fill="#080c16" stroke="#38bdf8" strokeWidth="2.5" />
                <text x={p.x} y={p.y - 10} fill="#fff" fontSize="11" fontWeight="700" textAnchor="middle">
                  {Math.round(p.temp)}°C
                </text>
                <text x={p.x} y={svgHeight - 10} fill="var(--text-muted)" fontSize="10" textAnchor="middle">
                  {p.time || '00:00'}
                </text>
              </g>
            ))}
          </svg>
        </div>

        {/* Hourly Metric Blocks Table */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${activeDayItems.length}, 1fr)`,
          gap: '0.5rem',
          marginTop: '1.25rem',
          overflowX: 'auto'
        }}>
          {activeDayItems.map((item, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(0, 0, 0, 0.25)',
                padding: '0.75rem 0.5rem',
                borderRadius: 'var(--radius-sm)',
                textAlign: 'center',
                minWidth: '85px'
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                {item.time.split(' ')[1]?.slice(0, 5) || item.time.split('T')[1]?.slice(0, 5)}
              </div>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '4px' }}>
                {item.condition}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                💧 {item.humidity}%
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                💨 {item.wind_speed} m/s
              </div>
              <div style={{
                fontSize: '0.72rem',
                fontWeight: 600,
                color: item.pop >= 0.4 ? 'var(--accent-cyan)' : 'var(--text-muted)',
                marginTop: '4px'
              }}>
                🌧️ {Math.round(item.pop * 100)}%
              </div>
            </div>
          ))}
        </div>

        <SourceAttribution source={source} note={attribution_notes} />
      </div>
    </div>
  );
}
