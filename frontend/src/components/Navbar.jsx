import React, { useState, useEffect, useRef } from 'react';
import { 
  CloudLightning, 
  Search, 
  MapPin, 
  Globe, 
  MessageSquare, 
  Calendar, 
  Sliders, 
  AlertTriangle, 
  CheckCircle2, 
  TrendingUp, 
  Cpu, 
  Crosshair 
} from 'lucide-react';
import { SUPPORTED_LANGUAGES, UI_TRANSLATIONS } from '../utils/constants';
import { searchLocations } from '../services/api';

export default function Navbar({ 
  currentCity, 
  onSelectCity, 
  currentLang, 
  onChangeLang, 
  activeTab, 
  onSelectTab,
  onUseGps
}) {
  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef(null);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (searchQuery.trim().length >= 2) {
        setIsSearching(true);
        try {
          const results = await searchLocations(searchQuery);
          setSearchResults(results);
          setShowDropdown(true);
        } catch (e) {
          setSearchResults([]);
        } finally {
          setIsSearching(false);
        }
      } else {
        setSearchResults([]);
        setShowDropdown(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Click outside listener for dropdown
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectLocation = (loc) => {
    onSelectCity(loc.name, loc.latitude, loc.longitude);
    setSearchQuery('');
    setShowDropdown(false);
  };

  const navItems = [
    { id: 'chat', label: t.navChat, icon: <MessageSquare size={16} /> },
    { id: 'forecast', label: t.navForecast, icon: <Calendar size={16} /> },
    { id: 'whatif', label: t.navWhatIf, icon: <Sliders size={16} /> },
    { id: 'alerts', label: t.navAlerts, icon: <AlertTriangle size={16} /> },
    { id: 'verify', label: t.navVerify, icon: <CheckCircle2 size={16} /> },
    { id: 'climate', label: t.navClimate, icon: <TrendingUp size={16} /> },
    { id: 'providers', label: t.navProviders, icon: <Cpu size={16} /> },
  ];

  return (
    <header className="navbar">
      <div className="nav-container">
        {/* Brand */}
        <div className="brand" style={{ cursor: 'pointer' }} onClick={() => onSelectTab('chat')}>
          <div className="brand-icon">
            <CloudLightning size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="brand-title">WEATHERGPT</span>
              <span className="brand-tag">SIH 2026</span>
            </div>
          </div>
        </div>

        {/* Desktop Nav Items */}
        <nav className="nav-links">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item-btn ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => onSelectTab(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Controls: Search, GPS, Language */}
        <div className="nav-controls">
          {/* City Search Bar with Autocomplete */}
          <div className="city-search-box" ref={searchRef}>
            <Search size={15} className="search-icon" />
            <input
              type="text"
              className="city-input"
              placeholder={t.searchCity}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => { if (searchResults.length > 0) setShowDropdown(true); }}
            />
            {showDropdown && searchResults.length > 0 && (
              <div style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                marginTop: '4px',
                background: 'rgba(15, 23, 42, 0.95)',
                backdropFilter: 'blur(16px)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                boxShadow: 'var(--shadow-card)',
                zIndex: 200,
                maxHeight: '220px',
                overflowY: 'auto'
              }}>
                {searchResults.map((loc, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleSelectLocation(loc)}
                    style={{
                      padding: '0.5rem 0.75rem',
                      cursor: 'pointer',
                      fontSize: '0.825rem',
                      borderBottom: '1px solid rgba(255,255,255,0.05)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(56, 189, 248, 0.15)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <MapPin size={13} style={{ color: 'var(--accent-cyan)' }} />
                    <span style={{ fontWeight: 600 }}>{loc.name}</span>
                    {loc.state && <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>({loc.state})</span>}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* GPS Button */}
          <button
            type="button"
            className="gps-btn"
            title={t.useGps}
            onClick={onUseGps}
          >
            <Crosshair size={18} />
          </button>

          {/* Language Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Globe size={16} style={{ color: 'var(--text-muted)' }} />
            <select
              className="lang-select"
              value={currentLang}
              onChange={(e) => onChangeLang(e.target.value)}
            >
              {SUPPORTED_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} style={{ background: '#0f172a' }}>
                  {l.native}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
}
