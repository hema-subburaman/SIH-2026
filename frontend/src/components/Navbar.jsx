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
  Crosshair,
  User,
  Menu,
  X,
  ChevronDown,
  MoreHorizontal
} from 'lucide-react';
import { SUPPORTED_LANGUAGES, SUPPORTED_PERSONAS, UI_TRANSLATIONS, getLocalizedPersona } from '../utils/constants';
import { searchLocations } from '../services/api';

export default function Navbar({ 
  currentCity, 
  onSelectCity, 
  currentLang, 
  onChangeLang, 
  currentPersona = 'general',
  onChangePersona,
  activeTab, 
  onSelectTab,
  onUseGps
}) {
  const t = UI_TRANSLATIONS[currentLang] || UI_TRANSLATIONS.en;
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const searchRef = useRef(null);
  const mobileSearchRef = useRef(null);
  const moreMenuRef = useRef(null);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);

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
    }, 280);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Click outside listener for dropdown and more menu
  useEffect(() => {
    function handleClickOutside(event) {
      const inDesktop = searchRef.current && searchRef.current.contains(event.target);
      const inMobile = mobileSearchRef.current && mobileSearchRef.current.contains(event.target);
      if (!inDesktop && !inMobile) {
        setShowDropdown(false);
      }
      if (moreMenuRef.current && !moreMenuRef.current.contains(event.target)) {
        setMoreMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectLocation = (loc) => {
    const displayName = loc.state ? `${loc.name}, ${loc.state}` : loc.name;
    onSelectCity(displayName, loc.latitude, loc.longitude);
    setSearchQuery('');
    setShowDropdown(false);
    setMobileMenuOpen(false);
  };

  const primaryNavItems = [
    { id: 'chat', label: t.navChat || 'Chat Assistant', shortLabel: 'Chat', icon: <MessageSquare size={16} /> },
    { id: 'forecast', label: t.navForecast || 'Forecast', shortLabel: 'Forecast', icon: <Calendar size={16} /> },
    { id: 'whatif', label: t.navWhatIf || 'What-If Impact', shortLabel: 'What-If', icon: <Sliders size={16} /> },
    { id: 'alerts', label: t.navAlerts || 'Alerts Center', shortLabel: 'Alerts', icon: <AlertTriangle size={16} /> },
  ];

  const secondaryNavItems = [
    { id: 'verify', label: t.navVerify || 'Verify Claim', shortLabel: 'Verify', icon: <CheckCircle2 size={16} /> },
    { id: 'climate', label: t.navClimate || 'Climate Trends', shortLabel: 'Climate', icon: <TrendingUp size={16} /> },
    { id: 'providers', label: t.navProviders || 'NWP & Providers', shortLabel: 'NWP Models', icon: <Cpu size={16} /> },
  ];

  const navItems = [...primaryNavItems, ...secondaryNavItems];
  const isSecondaryActive = secondaryNavItems.some(item => item.id === activeTab);

  const handleMobileNavClick = (id) => {
    onSelectTab(id);
    setMobileMenuOpen(false);
  };

  return (
    <header className="navbar">
      <div className="nav-container">
        {/* Brand */}
        <div className="brand" style={{ cursor: 'pointer' }} onClick={() => onSelectTab('chat')}>
          <div className="brand-icon">
            <CloudLightning size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span className="brand-title">WEATHERGPT</span>
              <span className="brand-tag">{t.brandBadge || 'INTELLIGENCE'}</span>
            </div>
          </div>
        </div>

        {/* Desktop Nav Items */}
        <nav className="nav-links">
          {/* Primary items: always shown on desktop/laptop */}
          {primaryNavItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item-btn ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => {
                onSelectTab(item.id);
                setMoreMenuOpen(false);
              }}
            >
              {item.icon}
              <span>{item.shortLabel}</span>
            </button>
          ))}

          {/* Secondary items: directly visible on ultra-wide desktop (>= 1500px) */}
          <div className="nav-secondary-direct">
            {secondaryNavItems.map((item) => (
              <button
                key={item.id}
                className={`nav-item-btn ${activeTab === item.id ? 'active' : ''}`}
                onClick={() => onSelectTab(item.id)}
              >
                {item.icon}
                <span>{item.shortLabel}</span>
              </button>
            ))}
          </div>

          {/* "More" dropdown: shown on laptop / standard desktop (1200px - 1499px) */}
          <div className="nav-more-wrapper" ref={moreMenuRef}>
            <button
              type="button"
              className={`nav-item-btn nav-more-btn ${isSecondaryActive ? 'active' : ''}`}
              onClick={() => setMoreMenuOpen(!moreMenuOpen)}
              aria-expanded={moreMenuOpen}
              aria-label="More navigation options"
            >
              <MoreHorizontal size={16} />
              <span>{isSecondaryActive ? (secondaryNavItems.find(i => i.id === activeTab)?.shortLabel || 'More') : (t.more || 'More')}</span>
              <ChevronDown size={14} style={{ transform: moreMenuOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s ease' }} />
            </button>

            {moreMenuOpen && (
              <div className="nav-more-dropdown glass-panel">
                {secondaryNavItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`nav-more-dropdown-item ${activeTab === item.id ? 'active' : ''}`}
                    onClick={() => {
                      onSelectTab(item.id);
                      setMoreMenuOpen(false);
                    }}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </nav>

        {/* Controls: Search, GPS, Persona, Language */}
        <div className="nav-controls">
          {/* City Search Bar with Real-Time Geocoding Autocomplete */}
          <div className="city-search-box" ref={searchRef}>
            <Search size={15} className="search-icon" />
            <input
              type="text"
              className="city-input"
              placeholder={t.searchCity}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => { if (searchResults.length > 0 || isSearching) setShowDropdown(true); }}
            />
            {showDropdown && (
              <div className="search-dropdown-menu">
                {isSearching && (
                  <div style={{ padding: '0.65rem 0.85rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {t.searchingLocations}
                  </div>
                )}
                {!isSearching && searchResults.length === 0 && searchQuery.trim().length >= 2 && (
                  <div style={{ padding: '0.65rem 0.85rem', fontSize: '0.8rem', color: 'var(--accent-amber)' }}>
                    {t.noLocationFound}
                  </div>
                )}
                {!isSearching && searchResults.map((loc, idx) => (
                  <div
                    key={idx}
                    className="search-dropdown-item"
                    onClick={() => handleSelectLocation(loc)}
                  >
                    <MapPin size={14} style={{ color: 'var(--accent-cyan)', flexShrink: 0 }} />
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span style={{ fontWeight: 600, color: '#f8fafc' }}>{loc.name}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: '6px' }}>
                        {[loc.district, loc.state, loc.country_name || loc.country].filter(Boolean).join(', ')}
                      </span>
                    </div>
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
            aria-label={t.useGps}
          >
            <Crosshair size={18} />
          </button>

          {/* Desktop Persona Selector */}
          <div className="desktop-control-item desktop-persona-control" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }} title={t.personalize}>
            <User size={15} style={{ color: 'var(--accent-indigo)' }} />
            <select
              className="lang-select persona-select"
              value={currentPersona}
              onChange={(e) => onChangePersona && onChangePersona(e.target.value)}
              style={{ maxWidth: '145px' }}
              aria-label={t.personalize}
            >
              {SUPPORTED_PERSONAS.map((p) => {
                const locP = getLocalizedPersona(p.id, currentLang);
                return (
                  <option key={p.id} value={p.id} style={{ background: '#0f172a' }}>
                    {locP.icon} {locP.label}
                  </option>
                );
              })}
            </select>
          </div>

          {/* Desktop Language Selector */}
          <div className="desktop-control-item desktop-lang-control" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }} title={t.language}>
            <Globe size={16} style={{ color: 'var(--text-muted)' }} />
            <select
              className="lang-select"
              value={currentLang}
              onChange={(e) => onChangeLang(e.target.value)}
              aria-label={t.language}
            >
              {SUPPORTED_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code} style={{ background: '#0f172a' }}>
                  {l.native}
                </option>
              ))}
            </select>
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label={mobileMenuOpen ? t.closeMenu : t.mobileMenu}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer / Full Navigation Overlay */}
      {mobileMenuOpen && (
        <div className="mobile-nav-drawer">
          {/* Mobile Drawer Location & GPS Section */}
          <div className="mobile-drawer-section">
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem' }}>
              {t.location || 'Location & Telemetry'}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <div style={{ position: 'relative', flex: 1 }} ref={mobileSearchRef}>
                <Search size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  className="city-input"
                  style={{ width: '100%', paddingLeft: '2.2rem' }}
                  placeholder={t.searchCity || 'Search city, town, village...'}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onFocus={() => { if (searchResults.length > 0 || isSearching) setShowDropdown(true); }}
                />
                {showDropdown && (
                  <div className="search-dropdown-menu">
                    {isSearching && (
                      <div style={{ padding: '0.65rem 0.85rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {t.searchingLocations}
                      </div>
                    )}
                    {!isSearching && searchResults.length === 0 && searchQuery.trim().length >= 2 && (
                      <div style={{ padding: '0.65rem 0.85rem', fontSize: '0.8rem', color: 'var(--accent-amber)' }}>
                        {t.noLocationFound}
                      </div>
                    )}
                    {!isSearching && searchResults.map((loc, idx) => (
                      <div
                        key={idx}
                        className="search-dropdown-item"
                        onClick={() => handleSelectLocation(loc)}
                      >
                        <MapPin size={14} style={{ color: 'var(--accent-cyan)', flexShrink: 0 }} />
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          <span style={{ fontWeight: 600, color: '#f8fafc' }}>{loc.name}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: '6px' }}>
                            {[loc.district, loc.state, loc.country_name || loc.country].filter(Boolean).join(', ')}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <button
                type="button"
                className="gps-btn"
                title={t.useGps}
                onClick={() => {
                  onUseGps();
                  setMobileMenuOpen(false);
                }}
                style={{ padding: '0.5rem', flexShrink: 0 }}
                aria-label={t.useGps}
              >
                <Crosshair size={18} />
              </button>
            </div>
          </div>

          <div className="mobile-drawer-section">
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem' }}>
              Navigation
            </div>
            <div className="mobile-drawer-links">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  className={`mobile-drawer-link-btn ${activeTab === item.id ? 'active' : ''}`}
                  onClick={() => handleMobileNavClick(item.id)}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="mobile-drawer-section">
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem' }}>
              {t.personalize}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <User size={16} style={{ color: 'var(--accent-indigo)' }} />
              <select
                className="lang-select"
                value={currentPersona}
                onChange={(e) => onChangePersona && onChangePersona(e.target.value)}
                style={{ width: '100%' }}
              >
                {SUPPORTED_PERSONAS.map((p) => {
                  const locP = getLocalizedPersona(p.id, currentLang);
                  return (
                    <option key={p.id} value={p.id} style={{ background: '#0f172a' }}>
                      {locP.icon} {locP.label}
                    </option>
                  );
                })}
              </select>
            </div>
          </div>

          <div className="mobile-drawer-section">
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '0.5rem' }}>
              {t.language}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Globe size={16} style={{ color: 'var(--text-muted)' }} />
              <select
                className="lang-select"
                value={currentLang}
                onChange={(e) => onChangeLang(e.target.value)}
                style={{ width: '100%' }}
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code} style={{ background: '#0f172a' }}>
                    {l.native} ({l.label})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
