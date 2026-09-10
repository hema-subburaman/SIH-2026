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
import { fetchForecast, analyzeRisk } from './services/api';
import { 
  MessageSquare, 
  Calendar, 
  Sliders, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp, 
  Cpu 
} from 'lucide-react';

export default function App() {
  const [currentCity, setCurrentCity] = useState('Chennai');
  const [coordinates, setCoordinates] = useState({ lat: 13.0827, lon: 80.2707 });
  const [currentLang, setCurrentLang] = useState('en');
  const [activeTab, setActiveTab] = useState('chat');

  const [weatherData, setWeatherData] = useState(null);
  const [riskData, setRiskData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [incomingAlert, setIncomingAlert] = useState(null);

  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;

  // Real-time Official Warning WebSocket dissemination
  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;
    let pingInterval = null;

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws/alerts`;

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
          reconnectTimeout = setTimeout(connect, 5000);
        };
        ws.onerror = () => {
          if (ws) ws.close();
        };
      } catch (e) {
        reconnectTimeout = setTimeout(connect, 5000);
      }
    }

    connect();

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  // Load weather and risk analysis whenever city or coordinates change
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchForecast(currentCity, coordinates?.lat, coordinates?.lon, 5);
        setWeatherData(data);

        // Compute base risk analysis for general outdoor activity
        if (data.current) {
          const riskRes = await analyzeRisk({
            activity: 'general_outdoor',
            temperature: data.current.temperature,
            feels_like: data.current.feels_like,
            humidity: data.current.humidity,
            wind_speed: data.current.wind_speed,
            condition: data.current.condition,
            pop: 0.0,
            visibility: data.current.visibility,
            target_time: 'Current',
            language: currentLang
          });
          setRiskData(riskRes);
        }
      } catch (err) {
        console.error('Failed to load weather data:', err);
        setError('Unable to load meteorological telemetry. Please verify backend service.');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [currentCity, coordinates?.lat, coordinates?.lon]);

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

  const mobileNavItems = [
    { id: 'chat', label: 'Chat', icon: <MessageSquare size={18} /> },
    { id: 'forecast', label: 'Forecast', icon: <Calendar size={18} /> },
    { id: 'whatif', label: 'What-If', icon: <Sliders size={18} /> },
    { id: 'alerts', label: 'Alerts', icon: <AlertTriangle size={18} /> },
    { id: 'verify', label: 'Verify', icon: <CheckCircle2 size={18} /> },
    { id: 'climate', label: 'Climate', icon: <TrendingUp size={18} /> },
    { id: 'providers', label: 'Models', icon: <Cpu size={18} /> },
  ];

  return (
    <div className="app-layout">
      {/* Top Navbar */}
      <Navbar
        currentCity={currentCity}
        onSelectCity={handleSelectCity}
        currentLang={currentLang}
        onChangeLang={setCurrentLang}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onUseGps={handleUseGps}
      />

      {/* Preset Cities Bar */}
      <div className="presets-bar">
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>Quick Locations:</span>
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
          />
        )}

        {activeTab === 'whatif' && (
          <WhatIfPage
            weatherData={weatherData}
            currentCity={currentCity}
          />
        )}

        {activeTab === 'alerts' && (
          <AlertsPage
            currentCity={currentCity}
            coordinates={coordinates}
          />
        )}

        {activeTab === 'verify' && (
          <VerifyClaimPage
            currentCity={currentCity}
            coordinates={coordinates}
          />
        )}

        {activeTab === 'climate' && (
          <ClimatePage
            currentCity={currentCity}
            coordinates={coordinates}
          />
        )}

        {activeTab === 'providers' && (
          <ProvidersPage />
        )}
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="mobile-bottom-nav">
        {mobileNavItems.map((item) => (
          <button
            key={item.id}
            className={`mobile-nav-btn ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => setActiveTab(item.id)}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
