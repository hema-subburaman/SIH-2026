import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import CurrentWeatherCard from './components/CurrentWeatherCard';
import AlertNotificationBanner from './components/AlertNotificationBanner';
import ChatPage from './pages/ChatPage';
import ForecastPage from './pages/ForecastPage';
import WhatIfPage from './pages/WhatIfPage';
import AlertsPage from './pages/AlertsPage';
import VerifyClaimPage from './pages/VerifyClaimPage';
import ClimatePage from './pages/ClimatePage';
import ProvidersPage from './pages/ProvidersPage';
import { PRESET_CITIES, UI_TRANSLATIONS } from './utils/constants';
import { fetchForecast, analyzeRisk, getAlertsWebSocketUrl } from './services/api';
import { 
  MessageSquare, 
  Calendar, 
  Sliders, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp, 
  Cpu,
  MoreHorizontal,
  X
} from 'lucide-react';

export default function App() {
  const [currentCity, setCurrentCity] = useState('Chennai');
  const [coordinates, setCoordinates] = useState({ lat: 13.0827, lon: 80.2707 });
  const [currentLang, setCurrentLang] = useState('en');
  const [currentPersona, setCurrentPersona] = useState(() => {
    return localStorage.getItem('weathergpt_persona') || 'general';
  });
  const [activeTab, setActiveTab] = useState('chat');
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);

  const [weatherData, setWeatherData] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [incomingAlert, setIncomingAlert] = useState(null);

  const handleSelectPersona = (newPersona) => {
    setCurrentPersona(newPersona);
    localStorage.setItem('weathergpt_persona', newPersona);
  };

  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;

  // Real-time Official Warning WebSocket dissemination
  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;
    let pingInterval = null;
    let isMounted = true;

    function connect() {
      if (!isMounted) return;
      const wsUrl = getAlertsWebSocketUrl();

      try {
        ws = new WebSocket(wsUrl);
        ws.onopen = () => {
          pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            }
          }, 30000);
        };
        ws.onmessage = (event) => {
          try {
            if (event.data === 'pong') return;
            const payload = JSON.parse(event.data);
            if (payload.type === 'OFFICIAL_WARNING_ALERT' && payload.alert) {
              setIncomingAlert(payload.alert);
            }
          } catch (e) {
            // Ignore keep-alive or heartbeat text
          }
        };
        ws.onclose = () => {
          clearInterval(pingInterval);
          if (isMounted) {
            reconnectTimeout = setTimeout(connect, 5000);
          }
        };
        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch (e) {
        if (isMounted) {
          reconnectTimeout = setTimeout(connect, 5000);
        }
      }
    }

    connect();

    return () => {
      isMounted = false;
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      if (ws) {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        } else if (ws.readyState === WebSocket.CONNECTING) {
          ws.onopen = () => {
            try { ws.close(); } catch (e) {}
          };
        }
      }
    };
  }, []);

  // Load weather forecast whenever city or coordinates change
  useEffect(() => {
    let isMounted = true;
    async function loadForecast() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchForecast(currentCity, coordinates?.lat, coordinates?.lon, 5);
        if (isMounted) {
          setWeatherData(data);
        }
      } catch (err) {
        console.error('Failed to load weather data:', err);
        if (isMounted) {
          setError('Unable to load meteorological telemetry. Please verify backend service.');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadForecast();
    return () => { isMounted = false; };
  }, [currentCity, coordinates?.lat, coordinates?.lon]);

  // Compute base risk analysis tailored to user persona & language without re-fetching forecast
  useEffect(() => {
    let isMounted = true;
    async function computeRisk() {
      if (!weatherData?.current) return;

      const personaToActivity = {
        farmer: 'farming',
        fisherman: 'marine_activity',
        traveler: 'travelling',
        construction: 'construction',
        aviation: 'aviation_briefing',
        events: 'outdoor_event',
        general: 'general_outdoor',
      };
      const targetActivity = personaToActivity[currentPersona] || 'general_outdoor';

      try {
        const riskRes = await analyzeRisk({
          activity: targetActivity,
          temperature: weatherData.current.temperature,
          feels_like: weatherData.current.feels_like,
          humidity: weatherData.current.humidity,
          wind_speed: weatherData.current.wind_speed,
          condition: weatherData.current.condition,
          pop: 0.0,
          visibility: weatherData.current.visibility,
          target_time: 'Current',
          language: currentLang
        });
        if (isMounted) {
          setRiskData(riskRes);
        }
      } catch (err) {
        console.warn('Risk analysis update failed:', err);
      }
    }

    computeRisk();
    return () => { isMounted = false; };
  }, [weatherData, currentPersona, currentLang]);

  const handleSelectCity = (name, lat, lon) => {
    setCurrentCity(name);
    if (lat && lon) {
      setCoordinates({ lat, lon });
    } else {
      setCoordinates(null);
    }
  };

  const handleUseGps = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        setCurrentCity(`Current Location (${latitude.toFixed(2)}, ${longitude.toFixed(2)})`);
        setCoordinates({ lat: latitude, lon: longitude });
      },
      (err) => {
        console.warn('Geolocation error:', err.message);
        alert('Location access was denied. Please select a city manually.');
      }
    );
  };

  const primaryMobileNavItems = [
    { id: 'chat', label: t.navChat || 'Chat Assistant', shortLabel: currentLang === 'hi' ? 'चैट' : (currentLang === 'ta' ? 'உரையாடல்' : 'Chat'), icon: <MessageSquare size={18} /> },
    { id: 'forecast', label: t.navForecast || 'Forecast', shortLabel: currentLang === 'hi' ? 'पूर्वानुमान' : (currentLang === 'ta' ? 'வானிலை' : 'Forecast'), icon: <Calendar size={18} /> },
    { id: 'whatif', label: t.navWhatIf || 'What-If Impact', shortLabel: 'What-If', icon: <Sliders size={18} /> },
    { id: 'alerts', label: t.navAlerts || 'Alerts Center', shortLabel: currentLang === 'hi' ? 'अलर्ट' : (currentLang === 'ta' ? 'எச்சரிக்கை' : 'Alerts'), icon: <AlertTriangle size={18} /> },
  ];

  const secondaryModules = [
    { 
      id: 'verify', 
      label: t.navVerify || 'Verify Claim', 
      desc: 'Verify viral weather posts or rumors against NWP ground truth', 
      icon: <CheckCircle2 size={18} style={{ color: 'var(--accent-emerald)' }} /> 
    },
    { 
      id: 'climate', 
      label: t.navClimate || 'Climate Trends', 
      desc: 'Decadal temperature anomalies & historical patterns', 
      icon: <TrendingUp size={18} style={{ color: 'var(--accent-cyan)' }} /> 
    },
    { 
      id: 'providers', 
      label: t.navProviders || 'NWP & Models', 
      desc: 'ECMWF, GFS, WRF multi-model consensus & telemetry', 
      icon: <Cpu size={18} style={{ color: 'var(--accent-indigo)' }} /> 
    },
  ];

  const secondaryIds = ['verify', 'climate', 'providers'];
  const isSecondaryActive = secondaryIds.includes(activeTab);

  return (
    <div className="app-layout">
      {/* Top Navbar */}
      <Navbar
        currentCity={currentCity}
        onSelectCity={handleSelectCity}
        currentLang={currentLang}
        onChangeLang={setCurrentLang}
        currentPersona={currentPersona}
        onChangePersona={handleSelectPersona}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onUseGps={handleUseGps}
      />

      {/* Preset Cities Bar */}
      <div className="presets-bar">
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
          {t.quickLocations || 'Quick Locations:'}
        </span>
        {PRESET_CITIES.map((c) => {
          const isActive = currentCity.toLowerCase().includes(c.name.toLowerCase());
          return (
            <button
              key={c.name}
              type="button"
              className={`preset-chip ${isActive ? 'active' : ''}`}
              onClick={() => handleSelectCity(c.name, c.lat, c.lon)}
            >
              {c.name}
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <main className="app-content">
        {/* Real-time Official Warning Broadcast Banner */}
        <AlertNotificationBanner
          incomingAlert={incomingAlert}
          onDismiss={() => setIncomingAlert(null)}
          currentLang={currentLang}
        />

        {/* Real-time Weather Summary Hero Card */}
        {weatherData && (
          <CurrentWeatherCard
            weatherData={weatherData}
            riskData={riskData}
            language={currentLang}
            onOpenWhatIf={() => setActiveTab('whatif')}
          />
        )}

        {/* Tab Views */}
        {activeTab === 'chat' && (
          <ChatPage
            currentCity={currentCity}
            currentLang={currentLang}
            coordinates={coordinates}
          />
        )}

        {activeTab === 'forecast' && (
          <ForecastPage
            forecastData={weatherData}
            currentCity={currentCity}
            coordinates={coordinates}
            currentLang={currentLang}
          />
        )}

        {activeTab === 'whatif' && (
          <WhatIfPage
            weatherData={weatherData}
            currentCity={currentCity}
            currentLang={currentLang}
          />
        )}

        {activeTab === 'alerts' && (
          <AlertsPage
            currentCity={currentCity}
            coordinates={coordinates}
            currentLang={currentLang}
          />
        )}

        {activeTab === 'verify' && (
          <VerifyClaimPage
            currentCity={currentCity}
            coordinates={coordinates}
            currentLang={currentLang}
          />
        )}

        {activeTab === 'climate' && (
          <ClimatePage
            currentCity={currentCity}
            coordinates={coordinates}
            currentLang={currentLang}
          />
        )}

        {activeTab === 'providers' && (
          <ProvidersPage
            currentCity={currentCity}
            currentLang={currentLang}
          />
        )}
      </main>

      {/* Mobile "More" Modules Bottom Sheet Overlay */}
      {mobileMoreOpen && (
        <div className="mobile-more-backdrop" onClick={() => setMobileMoreOpen(false)}>
          <div className="mobile-more-sheet glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="mobile-more-sheet-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sliders size={16} style={{ color: 'var(--accent-cyan)' }} />
                <span style={{ fontWeight: 700, fontSize: '0.88rem', color: '#fff' }}>
                  Additional Meteorological Modules
                </span>
              </div>
              <button 
                type="button" 
                className="mobile-more-sheet-close"
                onClick={() => setMobileMoreOpen(false)}
                aria-label="Close modules menu"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mobile-more-items-list">
              {secondaryModules.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className={`mobile-more-module-btn ${activeTab === m.id ? 'active' : ''}`}
                  onClick={() => {
                    setActiveTab(m.id);
                    setMobileMoreOpen(false);
                  }}
                >
                  <div className="mobile-more-module-icon">{m.icon}</div>
                  <div className="mobile-more-module-text">
                    <div className="mobile-more-module-title">{m.label}</div>
                    <div className="mobile-more-module-desc">{m.desc}</div>
                  </div>
                  {activeTab === m.id && (
                    <span className="mobile-more-active-dot" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Mobile Bottom Navigation — Compact 5-Item Bar */}
      <nav className="mobile-bottom-nav">
        {primaryMobileNavItems.map((item) => (
          <button
            key={item.id}
            className={`mobile-nav-btn ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(item.id);
              setMobileMoreOpen(false);
            }}
          >
            {item.icon}
            <span>{item.shortLabel || item.label}</span>
          </button>
        ))}

        {/* 5th Navigation Button: More */}
        <button
          key="more-nav-btn"
          type="button"
          className={`mobile-nav-btn ${isSecondaryActive || mobileMoreOpen ? 'active' : ''}`}
          onClick={() => setMobileMoreOpen(!mobileMoreOpen)}
          aria-expanded={mobileMoreOpen}
          aria-label="More navigation modules"
        >
          <MoreHorizontal size={18} />
          <span>
            {isSecondaryActive
              ? (secondaryModules.find(m => m.id === activeTab)?.label.split(' ')[0] || 'More')
              : (t.more || 'More')}
          </span>
        </button>
      </nav>
    </div>
  );
}
