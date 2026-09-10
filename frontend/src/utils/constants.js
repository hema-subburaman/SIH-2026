export const SUPPORTED_LANGUAGES = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
];

export const SUPPORTED_PERSONAS = [
  { id: 'general', label: 'General Public', icon: '🌤️', desc: 'Daily weather, air comfort, and routine commute' },
  { id: 'farmer', label: 'Farmer / Agriculture', icon: '🌾', desc: 'Crop spraying, rainfall timing, and irrigation' },
  { id: 'fisherman', label: 'Fisherman / Marine', icon: '⚓', desc: 'Sea state, wind gusts, and coastal storm safety' },
  { id: 'traveler', label: 'Traveler / Logistics', icon: '🚗', desc: 'Highway driving, fog visibility, and travel buffer' },
  { id: 'construction', label: 'Construction', icon: '🏗️', desc: 'Scaffolding, crane safety, and worker heat stress' },
  { id: 'aviation', label: 'Aviation Briefing', icon: '✈️', desc: 'VFR/IFR visibility, crosswinds, and convective CAPE' },
  { id: 'events', label: 'Outdoor Events', icon: '🎪', desc: 'Outdoor suitability score and rain contingency' },
];

export const PRESET_CITIES = [
  { name: 'Chennai', state: 'Tamil Nadu', lat: 13.0827, lon: 80.2707 },
  { name: 'Delhi', state: 'Delhi', lat: 28.6139, lon: 77.2090 },
  { name: 'Mumbai', state: 'Maharashtra', lat: 19.0760, lon: 72.8777 },
  { name: 'Bengaluru', state: 'Karnataka', lat: 12.9716, lon: 77.5946 },
  { name: 'Kolkata', state: 'West Bengal', lat: 22.5726, lon: 88.3639 },
  { name: 'Hyderabad', state: 'Telangana', lat: 17.3850, lon: 78.4867 },
];

export const ACTIVITIES = [
  { id: 'general_outdoor', label: 'General Outdoor', icon: 'Sun' },
  { id: 'running', label: 'Running / Jogging', icon: 'Footprints' },
  { id: 'walking', label: 'Walking', icon: 'Footprints' },
  { id: 'cycling', label: 'Cycling', icon: 'Bike' },
  { id: 'outdoor_event', label: 'Outdoor Event / Gathering', icon: 'Tent' },
  { id: 'travelling', label: 'Highway Travel / Transit', icon: 'Car' },
  { id: 'farming', label: 'Farming & Spraying', icon: 'Wheat' },
  { id: 'agriculture', label: 'Crop Harvesting / Irrigation', icon: 'Sprout' },
  { id: 'construction', label: 'Construction & Scaffolding', icon: 'HardHat' },
  { id: 'marine_activity', label: 'Marine / Coastal Fishing', icon: 'Anchor' },
  { id: 'aviation_briefing', label: 'Aviation Briefing', icon: 'Plane' },
];

import { UI_TRANSLATIONS } from './translations';

export { UI_TRANSLATIONS };

export function getLocalizedPersona(personaId, lang = 'en') {
  const t = UI_TRANSLATIONS[lang] || UI_TRANSLATIONS.en;
  const p = SUPPORTED_PERSONAS.find((x) => x.id === personaId);
  return {
    id: personaId,
    icon: p?.icon || '🌤️',
    label: t[`persona_${personaId}`] || p?.label || personaId,
    desc: t[`persona_${personaId}_desc`] || p?.desc || '',
  };
}

export function getLocalizedActivity(activityId, lang = 'en') {
  const t = UI_TRANSLATIONS[lang] || UI_TRANSLATIONS.en;
  const a = ACTIVITIES.find((x) => x.id === activityId);
  return {
    id: activityId,
    icon: a?.icon || 'Sun',
    label: t[`act_${activityId}`] || a?.label || activityId,
  };
}

export function getLocalizedTimeframe(timeId, lang = 'en') {
  const t = UI_TRANSLATIONS[lang] || UI_TRANSLATIONS.en;
  return t[`time_${timeId}`] || timeId;
}

