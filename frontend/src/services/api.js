const rawApiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const API_BASE = rawApiBase.endsWith('/') ? rawApiBase.slice(0, -1) : rawApiBase;

// In-memory response cache and in-flight promise map for request coalescing
const apiCache = new Map();
const inFlightRequests = new Map();

/**
 * Executes a GET request with in-flight coalescing and short-term client caching.
 * Prevents identical concurrent requests from firing multiple network roundtrips.
 */
export async function cachedFetch(url, options = {}, ttlMs = 60000) {
  const isGet = !options.method || options.method.toUpperCase() === 'GET';
  if (!isGet) {
    return fetch(url, options);
  }

  const cacheKey = url;
  const now = Date.now();

  // Return fresh cached data if within TTL
  const cached = apiCache.get(cacheKey);
  if (cached && (now - cached.timestamp < ttlMs)) {
    return cached.data;
  }

  // Return in-flight promise if an identical request is already running
  if (inFlightRequests.has(cacheKey)) {
    return inFlightRequests.get(cacheKey);
  }

  const promise = (async () => {
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        throw new Error(`API error (${res.status}): ${res.statusText}`);
      }
      const data = await res.json();
      apiCache.set(cacheKey, { data, timestamp: Date.now() });
      return data;
    } finally {
      inFlightRequests.delete(cacheKey);
    }
  })();

  inFlightRequests.set(cacheKey, promise);
  return promise;
}

export function clearClientApiCache() {
  apiCache.clear();
  inFlightRequests.clear();
}

export async function fetchCurrentWeather(city = 'Chennai', lat = null, lon = null, provider = null) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  if (provider) params.append('provider', provider);

  return await cachedFetch(`${API_BASE}/weather/current?${params.toString()}`, {}, 60000);
}

export async function fetchForecast(city = 'Chennai', lat = null, lon = null, days = 5, provider = null) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  params.append('days', days);
  if (provider) params.append('provider', provider);

  return await cachedFetch(`${API_BASE}/weather/forecast?${params.toString()}`, {}, 60000);
}

export async function fetchDetailedForecast(city = 'Chennai', lat = null, lon = null, days = 7) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  params.append('days', days);

  return await cachedFetch(`${API_BASE}/weather/forecast/detailed?${params.toString()}`, {}, 60000);
}

export async function searchLocations(query) {
  if (!query || query.trim().length === 0) return [];
  try {
    return await cachedFetch(`${API_BASE}/weather/location?query=${encodeURIComponent(query)}`, {}, 120000);
  } catch (e) {
    return [];
  }
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

  return await cachedFetch(`${API_BASE}/alerts?${params.toString()}`, {}, 30000);
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

  return await cachedFetch(`${API_BASE}/climate/history?${params.toString()}`, {}, 300000);
}

export async function fetchProvidersStatus() {
  return await cachedFetch(`${API_BASE}/providers/status`, {}, 30000);
}

export async function fetchModelComparison(city = 'Chennai', lat = null, lon = null, days = 5) {
  const params = new URLSearchParams();
  if (city) params.append('city', city);
  if (lat !== null) params.append('lat', lat);
  if (lon !== null) params.append('lon', lon);
  params.append('days', days);

  return await cachedFetch(`${API_BASE}/weather/forecast/compare?${params.toString()}`, {}, 60000);
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
  return await cachedFetch(`${API_BASE}/preferences/advisory?${params.toString()}`, {}, 60000);
}

/**
 * Resolves the real-time Alert WebSocket URL.
 * - Respects VITE_WS_URL environment variable if provided (e.g. wss://sih-2026-backend-kdio.onrender.com/ws/alerts).
 * - If VITE_API_BASE_URL is set to a remote backend (e.g. on Render), automatically derives the WebSocket endpoint.
 * - In local development (localhost / 127.0.0.1), connects directly to the FastAPI
 *   backend on port 8000 (ws://127.0.0.1:8000/ws/alerts), decoupled from the frontend Vite port (5173/5174).
 * - Falls back to current host ws(s)://<host>/ws/alerts.
 */
export function getAlertsWebSocketUrl() {
  if (import.meta.env?.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }

  // If VITE_API_BASE_URL points to a remote backend (e.g. on Render),
  // automatically derive the WebSocket endpoint if VITE_WS_URL wasn't explicitly defined.
  if (import.meta.env?.VITE_API_BASE_URL) {
    try {
      const apiUrl = new URL(import.meta.env.VITE_API_BASE_URL, window.location.origin);
      if (apiUrl.host && apiUrl.hostname !== 'localhost' && apiUrl.hostname !== '127.0.0.1') {
        const wsProtocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${wsProtocol}//${apiUrl.host}/ws/alerts`;
      }
    } catch (e) {
      // Fall through to standard resolution
    }
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


