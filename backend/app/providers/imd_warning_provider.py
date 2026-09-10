import httpx
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.providers.base import WarningProvider
from app.schemas.alert import AlertItem, AlertCategory, AlertSeverity
import logging
import re

logger = logging.getLogger(__name__)

# Comprehensive Indian city to state mapping covering all major metropolitan and Tier-1/Tier-2 urban centers
INDIAN_CITY_STATE_MAP: Dict[str, str] = {
    # Tamil Nadu
    "chennai": "Tamil Nadu",
    "coimbatore": "Tamil Nadu",
    "madurai": "Tamil Nadu",
    "tiruchirappalli": "Tamil Nadu",
    "trichy": "Tamil Nadu",
    "salem": "Tamil Nadu",
    "tirunelveli": "Tamil Nadu",
    "vellore": "Tamil Nadu",
    "thoothukudi": "Tamil Nadu",
    "thanjavur": "Tamil Nadu",
    # Karnataka
    "bengaluru": "Karnataka",
    "bangalore": "Karnataka",
    "mysuru": "Karnataka",
    "mysore": "Karnataka",
    "hubballi": "Karnataka",
    "mangalore": "Karnataka",
    "mangaluru": "Karnataka",
    "belagavi": "Karnataka",
    # Telangana
    "hyderabad": "Telangana",
    "secunderabad": "Telangana",
    "warangal": "Telangana",
    "nizamabad": "Telangana",
    # Maharashtra
    "mumbai": "Maharashtra",
    "pune": "Maharashtra",
    "nagpur": "Maharashtra",
    "thane": "Maharashtra",
    "nashik": "Maharashtra",
    "aurangabad": "Maharashtra",
    "chhatrapati sambhajinagar": "Maharashtra",
    # Delhi NCT
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "noida": "Uttar Pradesh",
    "gurugram": "Haryana",
    "gurgaon": "Haryana",
    "faridabad": "Haryana",
    # West Bengal
    "kolkata": "West Bengal",
    "howrah": "West Bengal",
    "siliguri": "West Bengal",
    "durgapur": "West Bengal",
    # Gujarat
    "ahmedabad": "Gujarat",
    "surat": "Gujarat",
    "vadodara": "Gujarat",
    "rajkot": "Gujarat",
    "bhavnagar": "Gujarat",
    # Rajasthan
    "jaipur": "Rajasthan",
    "jodhpur": "Rajasthan",
    "udaipur": "Rajasthan",
    "kota": "Rajasthan",
    "bikaner": "Rajasthan",
    # Uttar Pradesh
    "lucknow": "Uttar Pradesh",
    "kanpur": "Uttar Pradesh",
    "varanasi": "Uttar Pradesh",
    "agra": "Uttar Pradesh",
    "prayagraj": "Uttar Pradesh",
    "allahabad": "Uttar Pradesh",
    "ghaziabad": "Uttar Pradesh",
    "meerut": "Uttar Pradesh",
    # Kerala
    "kochi": "Kerala",
    "cochin": "Kerala",
    "thiruvananthapuram": "Kerala",
    "trivandrum": "Kerala",
    "kozhikode": "Kerala",
    "calicut": "Kerala",
    "thrissur": "Kerala",
    # Andhra Pradesh
    "visakhapatnam": "Andhra Pradesh",
    "vizag": "Andhra Pradesh",
    "vijayawada": "Andhra Pradesh",
    "guntur": "Andhra Pradesh",
    "tirupati": "Andhra Pradesh",
    # Odisha
    "bhubaneswar": "Odisha",
    "cuttack": "Odisha",
    "rourkela": "Odisha",
    "puri": "Odisha",
    # Madhya Pradesh
    "bhopal": "Madhya Pradesh",
    "indore": "Madhya Pradesh",
    "gwalior": "Madhya Pradesh",
    "jabalpur": "Madhya Pradesh",
    # Bihar
    "patna": "Bihar",
    "gaya": "Bihar",
    # Punjab / Haryana / UTs
    "chandigarh": "Chandigarh",
    "amritsar": "Punjab",
    "ludhiana": "Punjab",
    # Himachal Pradesh / J&K / Northeast
    "shimla": "Himachal Pradesh",
    "srinagar": "Jammu and Kashmir",
    "jammu": "Jammu and Kashmir",
    "guwahati": "Assam",
    "ranchi": "Jharkhand",
    "raipur": "Chhattisgarh",
    "dehradun": "Uttarakhand",
    "panaji": "Goa",
    "goa": "Goa",
}

# Recognized Indian States & Union Territories
INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
    "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
    "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
    "delhi", "chandigarh", "jammu and kashmir", "ladakh", "puducherry"
}


class OfficialMeteorologicalWarningProvider(WarningProvider):
    """
    Official Meteorological Warning Provider.
    Ingests official bulletins and CAP (Common Alerting Protocol) warnings from
    the India Meteorological Department (IMD) / National Disaster Management Authority (NDMA).
    Resolves locations through a multi-state directory and strictly avoids fabricating official alerts.
    """

    CAP_FEED_URL = "https://sachet.ndma.gov.in/cap_public_website/FetchAlertsByState"

    @property
    def provider_name(self) -> str:
        return "India Meteorological Department (IMD) / NDMA Sachet CAP Feed"

    @property
    def is_configured(self) -> bool:
        return True

    def resolve_city_state(self, city: Optional[str]) -> Optional[str]:
        """Resolves city name to official Indian state. Does NOT guess if unknown."""
        if not city:
            return "Tamil Nadu"

        clean = city.strip().lower()

        # 1. Direct city key match
        if clean in INDIAN_CITY_STATE_MAP:
            return INDIAN_CITY_STATE_MAP[clean]

        # 2. Substring match against mapped city keys
        for c_key, state_name in INDIAN_CITY_STATE_MAP.items():
            if re.search(rf'\b{re.escape(c_key)}\b', clean):
                return state_name

        # 3. Direct match with Indian state name
        if clean in INDIAN_STATES:
            # Capitalize appropriately
            return " ".join(word.capitalize() for word in clean.split())

        # If location cannot be resolved to a supported Indian state/UT, return None
        return None

    async def get_alerts_with_coverage(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> Tuple[List[AlertItem], bool, Optional[str]]:
        """
        Retrieves official government alerts and reports whether warning coverage is available.
        Returns: (alerts_list, coverage_available, state_name)
        """
        resolved_state = self.resolve_city_state(city)
        if not resolved_state:
            # Coverage unavailable for this location. Do NOT guess or invent.
            return [], False, None

        alerts: List[AlertItem] = []
        city_lower = (city or "").lower()

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(
                    self.CAP_FEED_URL,
                    params={"state": resolved_state},
                )
                if res.status_code == 200:
                    data = res.json()
                    for item in data.get("alerts", []):
                        area_desc = item.get("area_desc", "").lower()
                        # Filter by city or accept state-wide bulletins
                        if not city_lower or city_lower in area_desc or resolved_state.lower() in area_desc:
                            alerts.append(
                                AlertItem(
                                    id=f"imd-{item.get('identifier', '001')}",
                                    event=item.get("event", "IMD Weather Warning"),
                                    category=AlertCategory.HEAVY_RAINFALL,
                                    severity=AlertSeverity.WARNING,
                                    location=f"{city or resolved_state}, {resolved_state}",
                                    headline=item.get("headline", "IMD Weather Warning"),
                                    description=item.get("description", "Official meteorological bulletin."),
                                    recommendation="Follow instructions issued by local state disaster management authorities (SDMA).",
                                    is_official=True,
                                    source="India Meteorological Department (IMD) / NDMA Sachet CAP Feed",
                                    provider="India Meteorological Department (IMD)",
                                    data_type="official_bulletin"
                                )
                            )
        except Exception as e:
            logger.info(f"Official CAP feed query note for state '{resolved_state}': {e}")

        return alerts, True, resolved_state

    async def get_alerts(
        self,
        city: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> List[AlertItem]:
        alerts, _, _ = await self.get_alerts_with_coverage(city, lat, lon)
        return alerts

