import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  Play, 
  HelpCircle, 
  ShieldAlert, 
  Footprints, 
  Bike, 
  Tent, 
  Car, 
  Wheat, 
  HardHat, 
  Anchor, 
  Plane, 
  Sun,
  Calendar,
  Sparkles,
  Info
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import ExplainableFactors from '../components/ExplainableFactors';
import SourceAttribution from '../components/SourceAttribution';
import { ACTIVITIES } from '../utils/constants';
import { analyzeRisk } from '../services/api';

export default function WhatIfPage({ weatherData, currentCity }) {
  const [selectedActivity, setSelectedActivity] = useState('running');
  const [selectedTime, setSelectedTime] = useState('tomorrow_evening');
  
  // Weather parameters for simulation (initialized from current weather or forecast)
  const [temp, setTemp] = useState(32);
  const [humidity, setHumidity] = useState(65);
  const [wind, setWind] = useState(4.5);
  const [condition, setCondition] = useState('Partly Cloudy');
  const [pop, setPop] = useState(0.2);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  // Sync initial values from active weatherData
  useEffect(() => {
    if (weatherData && weatherData.current) {
      setTemp(Math.round(weatherData.current.temperature));
      setHumidity(weatherData.current.humidity);
      setWind(weatherData.current.wind_speed);
      setCondition(weatherData.current.condition);
    }
  }, [weatherData]);

  const runSimulation = async () => {
    setLoading(true);
    try {
      const response = await analyzeRisk({
        activity: selectedActivity,
        temperature: parseFloat(temp),
        humidity: parseInt(humidity, 10),
        wind_speed: parseFloat(wind),
        condition: condition,
        pop: parseFloat(pop),
        target_time: selectedTime,
        language: 'en'
      });
      setResult(response);
    } catch (err) {
      console.error('Simulation error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Run automatically on first mount or activity change
  useEffect(() => {
    runSimulation();
  }, [selectedActivity, selectedTime]);

  const timeSlots = [
    { id: 'now', label: 'Current Conditions' },
    { id: 'tomorrow_morning', label: 'Tomorrow Morning (07:00)' },
    { id: 'tomorrow_afternoon', label: 'Tomorrow Midday (14:00)' },
    { id: 'tomorrow_evening', label: 'Tomorrow Evening (18:30)' },
    { id: 'weekend', label: 'This Weekend' },
  ];

  const getActivityIcon = (id) => {
    switch (id) {
      case 'running': return <Footprints size={18} />;
      case 'walking': return <Footprints size={18} />;
      case 'cycling': return <Bike size={18} />;
      case 'outdoor_event': return <Tent size={18} />;
      case 'travelling': return <Car size={18} />;
      case 'farming': return <Wheat size={18} />;
      case 'agriculture': return <Wheat size={18} />;
      case 'construction': return <HardHat size={18} />;
      case 'marine_activity': return <Anchor size={18} />;
      case 'aviation_briefing': return <Plane size={18} />;
      default: return <Sun size={18} />;
    }
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sliders size={22} style={{ color: 'var(--accent-cyan)' }} />
          <span>What-If Scenario & Impact Simulator</span>
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Evaluate activity-specific feasibility and risk against forecast conditions in <strong>{currentCity}</strong>.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: '1.5rem' }}>
        {/* Left Column: Scenario Controls */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '1rem', color: '#fff' }}>
            1. Select Target Activity
          </h3>

          {/* Activity Cards Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: '0.6rem',
            marginBottom: '1.5rem'
          }}>
            {ACTIVITIES.map((act) => {
              const isSelected = selectedActivity === act.id;
              return (
                <button
                  key={act.id}
                  type="button"
                  onClick={() => setSelectedActivity(act.id)}
                  style={{
                    background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'rgba(0, 0, 0, 0.3)',
                    border: `1px solid ${isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.65rem 0.75rem',
                    color: isSelected ? '#fff' : 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    cursor: 'pointer',
                    textAlign: 'left',
                    fontFamily: 'inherit',
                    fontSize: '0.825rem',
                    fontWeight: isSelected ? 600 : 500,
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span style={{ color: isSelected ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                    {getActivityIcon(act.id)}
                  </span>
                  <span>{act.label}</span>
                </button>
              );
            })}
          </div>

          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem', color: '#fff' }}>
            2. Timeframe Selection
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem' }}>
            {timeSlots.map((ts) => (
              <button
                key={ts.id}
                type="button"
                className={`preset-chip ${selectedTime === ts.id ? 'active' : ''}`}
                onClick={() => setSelectedTime(ts.id)}
              >
                {ts.label}
              </button>
            ))}
          </div>

          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem', color: '#fff' }}>
            3. Meteorological Parameters (Simulated)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Temperature: <strong>{temp}°C</strong>
              </label>
              <input
                type="range"
                min="10"
                max="48"
                value={temp}
                onChange={(e) => setTemp(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Relative Humidity: <strong>{humidity}%</strong>
              </label>
              <input
                type="range"
                min="20"
                max="100"
                value={humidity}
                onChange={(e) => setHumidity(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Wind Speed: <strong>{wind} m/s</strong> (~{Math.round(wind * 3.6)} km/h)
              </label>
              <input
                type="range"
                min="0"
                max="25"
                step="0.5"
                value={wind}
                onChange={(e) => setWind(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                Rain Probability: <strong>{Math.round(pop * 100)}%</strong>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={pop}
                onChange={(e) => setPop(e.target.value)}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          <button
            type="button"
            className="send-btn"
            style={{ width: '100%', justifyContent: 'center', marginTop: '1.5rem' }}
            onClick={runSimulation}
            disabled={loading}
          >
            <Play size={16} />
            <span>Recalculate Impact</span>
          </button>
        </div>

        {/* Right Column: Calculated Impact & Explainable Factors */}
        <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Decision-Support Output
                </span>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, textTransform: 'capitalize' }}>
                  {selectedActivity.replace('_', ' ')}
                </h3>
              </div>

              {result && <RiskBadge level={result.risk_level} score={result.score} />}
            </div>

            {loading ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                Evaluating atmospheric stress factors against tolerance matrix...
              </div>
            ) : result ? (
              <div>
                <ExplainableFactors
                  factors={result.factors}
                  explanation={result.explanation}
                  recommendation={result.recommendation}
                />

                <div style={{
                  marginTop: '1.25rem',
                  padding: '0.75rem',
                  background: 'rgba(255, 255, 255, 0.02)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.72rem',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border-subtle)'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '4px', color: 'var(--accent-amber)' }}>
                    <Info size={13} />
                    <strong>SIH Decision-Support Protocol</strong>
                  </div>
                  <div>{result.disclaimer}</div>
                </div>
              </div>
            ) : null}
          </div>

          <SourceAttribution
            source="Weather Impact Intelligence Engine"
            note="Rule-based heuristic impact modeling"
          />
        </div>
      </div>
    </div>
  );
}
