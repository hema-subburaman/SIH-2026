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
