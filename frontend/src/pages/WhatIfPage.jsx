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
  Info,
  Clock,
  MessageSquare
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import ExplainableFactors from '../components/ExplainableFactors';
import SourceAttribution from '../components/SourceAttribution';
import { ACTIVITIES, UI_TRANSLATIONS, getLocalizedActivity, getLocalizedTimeframe } from '../utils/constants';
import { analyzeRisk } from '../services/api';

export default function WhatIfPage({ weatherData, currentCity, currentLang = 'en' }) {
  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
  const [selectedActivity, setSelectedActivity] = useState('running');
  const [selectedTime, setSelectedTime] = useState('tomorrow_evening');
  const [customScenario, setCustomScenario] = useState('');
  
  // Weather parameters for simulation (initialized from current weather or forecast)
  const [temp, setTemp] = useState(32);
  const [humidity, setHumidity] = useState(65);
  const [wind, setWind] = useState(4.5);
  const [condition, setCondition] = useState('Partly Cloudy');
  const [rainPop, setRainPop] = useState(20);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  // Sync initial values from active weatherData
  useEffect(() => {
    if (weatherData && weatherData.current) {
      setTemp(Math.round(weatherData.current.temperature));
      setHumidity(weatherData.current.humidity);
      setWind(weatherData.current.wind_speed);
      setCondition(weatherData.current.condition);
      if (weatherData.current.pop !== undefined) {
        setRainPop(Math.round(weatherData.current.pop * 100));
      }
    }
  }, [weatherData]);

  // Numeric input synchronization & validation helpers
  const handleNumericChange = (val, setter, min, max, isFloat = false) => {
    if (val === '') {
      setter('');
      return;
    }
    const parsed = isFloat ? parseFloat(val) : parseInt(val, 10);
    if (!isNaN(parsed)) {
      setter(parsed);
    }
  };

  const handleNumericBlur = (val, setter, fallback, min, max, isFloat = false) => {
    const parsed = isFloat ? parseFloat(val) : parseInt(val, 10);
    if (isNaN(parsed) || val === '') {
      setter(fallback);
    } else {
      setter(Math.min(max, Math.max(min, parsed)));
    }
  };

  const getSanitized = (val, fallback, min, max, isFloat = false) => {
    const parsed = isFloat ? parseFloat(val) : parseInt(val, 10);
    if (isNaN(parsed) || !isFinite(parsed)) return fallback;
    return Math.min(max, Math.max(min, parsed));
  };

  const timeSlots = [
    { id: 'current', label: getLocalizedTimeframe('current', currentLang) },
    { id: 'tomorrow_morning', label: getLocalizedTimeframe('tomorrow_morning', currentLang) },
    { id: 'tomorrow_midday', label: getLocalizedTimeframe('tomorrow_midday', currentLang) },
    { id: 'tomorrow_evening', label: getLocalizedTimeframe('tomorrow_evening', currentLang) },
    { id: 'weekend', label: getLocalizedTimeframe('weekend', currentLang) },
  ];

  // Update parameters when user chooses a specific timeframe slot
  useEffect(() => {
    if (!weatherData || !weatherData.forecast) return;

    if (selectedTime === 'current' && weatherData.current) {
      setTemp(Math.round(weatherData.current.temperature));
      setHumidity(weatherData.current.humidity);
      setWind(weatherData.current.wind_speed);
      setCondition(weatherData.current.condition);
      setRainPop(weatherData.current.pop !== undefined ? Math.round(weatherData.current.pop * 100) : 20);
      return;
    }

    const todayStr = new Date().toISOString().split('T')[0];
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowStr = tomorrow.toISOString().split('T')[0];

    let targetItem = null;

    if (selectedTime === 'tomorrow_morning') {
      targetItem = weatherData.forecast.find(i => i.time.startsWith(tomorrowStr) && (i.time.includes('06:00') || i.time.includes('09:00')));
    } else if (selectedTime === 'tomorrow_midday') {
      targetItem = weatherData.forecast.find(i => i.time.startsWith(tomorrowStr) && (i.time.includes('12:00') || i.time.includes('15:00')));
    } else if (selectedTime === 'tomorrow_evening') {
      targetItem = weatherData.forecast.find(i => i.time.startsWith(tomorrowStr) && (i.time.includes('18:00') || i.time.includes('21:00')));
    } else if (selectedTime === 'weekend') {
      targetItem = weatherData.forecast.find(i => {
        const d = new Date(i.time.split(' ')[0]);
        return d.getDay() === 0 || d.getDay() === 6;
      });
    }

    if (targetItem) {
      setTemp(Math.round(targetItem.temperature));
      setHumidity(targetItem.humidity);
      setWind(targetItem.wind_speed);
      setCondition(targetItem.condition);
      setRainPop(Math.round((targetItem.pop || 0) * 100));
    }
  }, [selectedTime, weatherData]);

  // Automatically recalculate baseline when activity, time, or language changes
  useEffect(() => {
    handleRecalculate();
  }, [selectedActivity, selectedTime, currentLang]);

  const handleRecalculate = async () => {
    setLoading(true);
    try {
      const sanitizedTemp = getSanitized(temp, 30, -20, 60);
      const sanitizedHumidity = getSanitized(humidity, 60, 0, 100);
      const sanitizedWind = getSanitized(wind, 5.0, 0, 80, true);
      const sanitizedRainPop = getSanitized(rainPop, 20, 0, 100);

      const res = await analyzeRisk({
        activity: selectedActivity,
        temperature: sanitizedTemp,
        feels_like: sanitizedTemp,
        humidity: sanitizedHumidity,
        wind_speed: sanitizedWind,
        condition: condition,
        pop: sanitizedRainPop / 100.0,
        target_time: selectedTime,
        custom_scenario: customScenario.trim() || undefined,
        language: currentLang
      });
      setResult(res);
    } catch (e) {
      console.error('What-If recalculation error:', e);
    } finally {
      setLoading(false);
    }
  };

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

  const getTimeLabel = (id) => {
    const slot = timeSlots.find(ts => ts.id === id);
    return slot ? slot.label : id.replace('_', ' ');
  };

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Sliders size={22} style={{ color: 'var(--accent-cyan)' }} />
          <span>{t.whatIfTitle || 'What-If Impact Simulator & Risk Modeling'}</span>
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          {t.whatIfSubtitle || 'Simulate atmospheric variations and evaluate sector-specific operational risk'} ({currentCity}).
        </p>
      </div>

      <div className="whatif-layout-grid">
        {/* Left Column: Scenario Controls */}
        <div className="glass-panel" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.85rem', color: '#fff' }}>
            {t.selectActivity || '1. Select Operational Activity'}
          </h3>

          {/* Activity Cards Grid */}
          <div className="whatif-activities-grid">
            {ACTIVITIES.map((act) => {
              const isSelected = selectedActivity === act.id;
              const locAct = getLocalizedActivity(act.id, currentLang);
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
                  <span>{locAct.label}</span>
                </button>
              );
            })}
          </div>

          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem', color: '#fff' }}>
            {t.selectTimeframe || '2. Select Forecast Horizon'}
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

          {/* Section 3: Custom Scenario Context */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                <Sparkles size={16} style={{ color: 'var(--accent-cyan)' }} />
                <span>{t.scenarioDescription || '3. Natural Language Custom Scenario'}</span>
              </h3>
            </div>
            <textarea
              value={customScenario}
              onChange={(e) => setCustomScenario(e.target.value)}
              placeholder={t.scenarioPlaceholder || 'Describe a custom atmospheric scenario (e.g. sudden downpour or high wind gusts)...'}
              rows={2}
              style={{
                width: '100%',
                boxSizing: 'border-box',
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.65rem 0.8rem',
                color: '#fff',
                fontSize: '0.85rem',
                fontFamily: 'inherit',
                resize: 'vertical',
                outline: 'none',
                lineHeight: '1.4',
                transition: 'border-color 0.15s ease'
              }}
              onFocus={(e) => { e.target.style.borderColor = 'var(--accent-cyan)'; }}
              onBlur={(e) => { e.target.style.borderColor = 'var(--border-subtle)'; }}
            />

            {/* Quick Context Presets */}
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.35rem', marginTop: '0.45rem' }}>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{t.scenarioChipsTitle || 'Try:'}</span>
              {[
                t.chip_rain_marathon || 'Heavy Rain during evening marathon',
                t.chip_heat_concrete || 'Extreme Heatwave during afternoon concrete pour',
                t.chip_wind_marine || 'High Wind Gusts on coastal fishing boat',
                t.chip_fog_transit || 'Morning Dense Fog on expressway transit'
              ].map((txt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setCustomScenario(txt)}
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '12px',
                    padding: '0.15rem 0.55rem',
                    fontSize: '0.7rem',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.color = 'var(--accent-cyan)';
                    e.target.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.color = 'var(--text-secondary)';
                    e.target.style.borderColor = 'var(--border-subtle)';
                  }}
                >
                  {txt}
                </button>
              ))}
            </div>
          </div>

          {/* Section 4: Meteorological Parameters (Simulated) */}
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem', color: '#fff' }}>
            {t.adjustParameters || '4. Fine-Tune Atmospheric Parameters'}
          </h3>
          <div className="whatif-params-grid">
            {/* Temperature */}
            <div style={{
              background: 'rgba(0, 0, 0, 0.25)',
              padding: '0.75rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t.temperature || 'Temperature'}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <input
                    type="number"
                    min="-20"
                    max="60"
                    value={temp}
                    onChange={(e) => handleNumericChange(e.target.value, setTemp, -20, 60)}
                    onBlur={(e) => handleNumericBlur(e.target.value, setTemp, 30, -20, 60)}
                    style={{
                      width: '48px',
                      padding: '2px 4px',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: 'var(--accent-cyan)',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      textAlign: 'right'
                    }}
                  />
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>°C</span>
                </div>
              </div>
              <input
                type="range"
                min="-20"
                max="60"
                value={typeof temp === 'number' ? temp : 30}
                onChange={(e) => setTemp(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
              />
            </div>

            {/* Humidity */}
            <div style={{
              background: 'rgba(0, 0, 0, 0.25)',
              padding: '0.75rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t.humidity || 'Humidity'}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={humidity}
                    onChange={(e) => handleNumericChange(e.target.value, setHumidity, 0, 100)}
                    onBlur={(e) => handleNumericBlur(e.target.value, setHumidity, 60, 0, 100)}
                    style={{
                      width: '48px',
                      padding: '2px 4px',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: 'var(--accent-cyan)',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      textAlign: 'right'
                    }}
                  />
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>%</span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={typeof humidity === 'number' ? humidity : 60}
                onChange={(e) => setHumidity(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
              />
            </div>

            {/* Wind Speed */}
            <div style={{
              background: 'rgba(0, 0, 0, 0.25)',
              padding: '0.75rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t.windSpeed || 'Wind Speed'}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="80"
                    value={wind}
                    onChange={(e) => handleNumericChange(e.target.value, setWind, 0, 80, true)}
                    onBlur={(e) => handleNumericBlur(e.target.value, setWind, 5.0, 0, 80, true)}
                    style={{
                      width: '52px',
                      padding: '2px 4px',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: 'var(--accent-cyan)',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      textAlign: 'right'
                    }}
                  />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>m/s</span>
                </div>
              </div>
              <input
                type="range"
                step="0.5"
                min="0"
                max="80"
                value={typeof wind === 'number' ? wind : 5.0}
                onChange={(e) => setWind(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
              />
            </div>

            {/* Rain Probability */}
            <div style={{
              background: 'rgba(0, 0, 0, 0.25)',
              padding: '0.75rem',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-subtle)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t.rainProbability || 'Rain Probability'}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={rainPop}
                    onChange={(e) => handleNumericChange(e.target.value, setRainPop, 0, 100)}
                    onBlur={(e) => handleNumericBlur(e.target.value, setRainPop, 20, 0, 100)}
                    style={{
                      width: '48px',
                      padding: '2px 4px',
                      background: 'rgba(15, 23, 42, 0.8)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '4px',
                      color: 'var(--accent-cyan)',
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      textAlign: 'right'
                    }}
                  />
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>%</span>
                </div>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={typeof rainPop === 'number' ? rainPop : 20}
                onChange={(e) => setRainPop(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
              />
            </div>
          </div>

          <button
            type="button"
            className="send-btn"
            onClick={handleRecalculate}
            disabled={loading}
            style={{ width: '100%', marginTop: '1.5rem', padding: '0.85rem' }}
          >
            <Play size={16} />
            <span>{loading ? (t.evaluatingRisk || 'Evaluating...') : (t.recalculateRisk || 'Recalculate Risk Analysis')}</span>
          </button>
        </div>

        {/* Right Column: Dynamic Risk Evaluation Output */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="glass-panel" style={{ padding: '1.5rem', flexGrow: 1 }}>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '1.25rem', color: '#fff' }}>
              {t.riskAssessment || 'Operational Risk Assessment'}
            </h3>

            {loading ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                {t.evaluatingRisk || 'Evaluating atmospheric matrices & threshold boundaries...'}
              </div>
            ) : result ? (
              <div>
                {/* Score and Activity Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  paddingBottom: '1.25rem',
                  borderBottom: '1px solid var(--border-subtle)',
                  marginBottom: '1.25rem',
                  flexWrap: 'wrap',
                  gap: '0.75rem'
                }}>
                  <div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {t.targetActivity || 'Target Activity'}
                    </div>
                    <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#fff', textTransform: 'capitalize' }}>
                      {getLocalizedActivity(selectedActivity, currentLang).label}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {t.simulationWindow || 'Window'}: <strong>{getTimeLabel(selectedTime)}</strong>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      {t.compositeScore || 'Composite Risk Score'}
                    </div>
                    <RiskBadge level={result.risk_level} score={result.risk_score} />
                  </div>
                </div>

                {/* Factors & Actionable Advisory */}
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
                    <strong>Decision-Support Protocol</strong>
                  </div>
                  <div>{result.disclaimer || t.decisionSupportProtocol}</div>
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
