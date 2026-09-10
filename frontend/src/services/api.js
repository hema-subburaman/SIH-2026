const API_BASE = '/api/v1';

export async function fetchCurrentWeather(city = 'Chennai', lat = null, lon = null, provider = null) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  if (provider) params.append('provider', provider);

  const res = await fetch(`${API_BASE}/weather/current?${params.toString()}`);
  if (!res.ok) throw new Error(`Weather API error: ${res.statusText}`);
  return await res.json();
}

export async function fetchForecast(city = 'Chennai', lat = null, lon = null, days = 5, provider = null) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  params.append('days', days);
  if (provider) params.append('provider', provider);

  const res = await fetch(`${API_BASE}/weather/forecast?${params.toString()}`);
  if (!res.ok) throw new Error(`Forecast API error: ${res.statusText}`);
  return await res.json();
}

export async function fetchDetailedForecast(city = 'Chennai', lat = null, lon = null, days = 7) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  params.append('days', days);

  const res = await fetch(`${API_BASE}/weather/forecast/detailed?${params.toString()}`);
  if (!res.ok) throw new Error(`Detailed Forecast API error: ${res.statusText}`);
  return await res.json();
}


export async function searchLocations(query) {
  if (!query || query.trim().length === 0) return [];
  const res = await fetch(`${API_BASE}/weather/location?query=${encodeURIComponent(query)}`);
  if (!res.ok) return [];
  return await res.json();
}

export async function queryChat(message, city = 'Chennai', lat = null, lon = null, language = 'en') {
  const res = await fetch(`${API_BASE}/chat/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, city, latitude: lat, longitude: lon, language }),
  });
  if (!res.ok) throw new Error(`Chat API error: ${res.statusText}`);
  return await res.json();
}

export async function analyzeRisk(payload) {
  const res = await fetch(`${API_BASE}/risk/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Risk Engine error: ${res.statusText}`);
  return await res.json();
}

export async function fetchAlerts(city = 'Chennai', lat = null, lon = null) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);

  const res = await fetch(`${API_BASE}/alerts?${params.toString()}`);
  if (!res.ok) throw new Error(`Alerts API error: ${res.statusText}`);
  return await res.json();
}

export async function verifyClaim(claim, city = 'Chennai', lat = null, lon = null, language = 'en') {
  const res = await fetch(`${API_BASE}/claim/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim, city, latitude: lat, longitude: lon, language }),
  });
  if (!res.ok) throw new Error(`Claim verification error: ${res.statusText}`);
  return await res.json();
}

export async function fetchClimateTrends(city = 'Chennai', lat = null, lon = null, years = 10) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  params.append('years', years);

  const res = await fetch(`${API_BASE}/climate/history?${params.toString()}`);
  if (!res.ok) throw new Error(`Climate trends error: ${res.statusText}`);
  return await res.json();
}

export async function fetchProvidersStatus() {
  const res = await fetch(`${API_BASE}/providers/status`);
  if (!res.ok) throw new Error(`Providers API error: ${res.statusText}`);
  return await res.json();
}

export async function fetchModelComparison(city = 'Chennai', lat = null, lon = null, days = 5) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  params.append('days', days);

  const res = await fetch(`${API_BASE}/weather/forecast/compare?${params.toString()}`);
  if (!res.ok) throw new Error(`Model comparison API error: ${res.statusText}`);
  return await res.json();
}

export async function fetchUserPreferences(sessionId = 'default_guest') {
  const res = await fetch(`${API_BASE}/preferences/`, {
    headers: { 'X-Session-ID': sessionId }
  });
  if (!res.ok) return { persona: 'general', default_city: 'Chennai', language: 'en' };
  return await res.json();
}

export async function updateUserPreferences(prefData, sessionId = 'default_guest') {
  const res = await fetch(`${API_BASE}/preferences/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId
    },
    body: JSON.stringify(prefData)
  });
  if (!res.ok) throw new Error('Failed to update preferences');
  return await res.json();
}

export async function fetchPersonalizedAdvisory(persona = 'general', city = 'Chennai') {
  const params = new URLSearchParams({ persona, city });
  const res = await fetch(`${API_BASE}/preferences/advisory?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch personalized advisory');
  return await res.json();
}

/**
 * Resolves the real-time Alert WebSocket URL.
 * - Respects VITE_WS_URL environment variable if provided.
 * - In local development (localhost / 127.0.0.1), connects directly to the FastAPI
 *   backend on port 8000 (ws://127.0.0.1:8000/ws/alerts), decoupled from the frontend Vite port (5173/5174).
 * - In production/deployment, connects to the current host under ws(s)://<host>/ws/alerts.
 */
export function getAlertsWebSocketUrl() {
  if (import.meta.env?.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }

  const isSecure = window.location.protocol === 'https:';
  const wsProtocol = isSecure ? 'wss:' : 'ws:';
  const hostname = window.location.hostname;

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    const backendPort = import.meta.env?.VITE_BACKEND_PORT || '8000';
    return `${wsProtocol}//127.0.0.1:${backendPort}/ws/alerts`;
  }

  return `${wsProtocol}//${window.location.host}/ws/alerts`;
}


