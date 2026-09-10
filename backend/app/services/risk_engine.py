from typing import List, Dict, Any, Optional
from app.schemas.risk import RiskLevel, RiskFactor, ActivityType, RiskAnalysisResponse
from app.core.config import settings
import math


class WeatherImpactIntelligenceEngine:
    """
    Core Weather Impact Intelligence Engine.
    Converts raw meteorological parameters into explainable risk assessments,
    identifying critical factors and synthesizing tailored activity-specific recommendations.
    
    Disclaimer: These prototype thresholds are derived from heuristic meteorological indices 
    (Heat Index, Beaufort scale, precipitation rate) and are not official medical or government safety standards.
    """

    def calculate_heat_index(self, temp_c: float, humidity: int) -> float:
        """Calculates Steadman/Rothfusz Heat Index in Celsius."""
        if temp_c < 26.7:
            return temp_c
        
        # Convert to Fahrenheit for standard Rothfusz regression equation
        t = (temp_c * 9.0 / 5.0) + 32.0
        r = float(humidity)
        
        hi = -42.379 + 2.04901523 * t + 10.14333127 * r - 0.22475541 * t * r \
             - 0.00683783 * (t ** 2) - 0.05481717 * (r ** 2) \
             + 0.00122874 * (t ** 2) * r + 0.00085282 * t * (r ** 2) \
             - 0.00000199 * (t ** 2) * (r ** 2)
             
        # Convert back to Celsius
        return round((hi - 32.0) * 5.0 / 9.0, 1)

    def analyze(
        self,
        activity: ActivityType,
        temperature: float,
        humidity: int,
        wind_speed: float,
        condition: str,
        pop: float = 0.0,
        feels_like: Optional[float] = None,
        visibility: Optional[float] = 10000.0,
        target_time: str = "Current",
        language: str = "en"
    ) -> RiskAnalysisResponse:
        factors: List[RiskFactor] = []
        score: float = 0.0  # 0 to 100 composite risk score
        
        # 1. Thermal Stress (Temperature, Humidity, Heat Index)
        effective_temp = feels_like if feels_like is not None else temperature
        heat_idx = self.calculate_heat_index(temperature, humidity)
        
        cond_lower = condition.lower()
        is_thunder = "thunder" in cond_lower or "lightning" in cond_lower or "storm" in cond_lower
        is_rain = "rain" in cond_lower or "drizzle" in cond_lower or pop >= 0.50
        is_fog = "fog" in cond_lower or "mist" in cond_lower or (visibility is not None and visibility < 2000)

        # Base evaluations
        # Heat Evaluation
        if heat_idx >= settings.HEAT_DANGER_TEMP:
            score += 35
            factors.append(
                RiskFactor(
                    parameter="Heat Index / Extreme Heat",
                    value=f"{heat_idx}°C (Temp: {temperature}°C, Humidity: {humidity}%)",
                    impact="Severe risk of heat exhaustion, dehydration, and heat stroke during sustained physical exertion.",
                    severity=RiskLevel.HIGH
                )
            )
        elif heat_idx >= settings.HEAT_CAUTION_TEMP:
            score += 18
            factors.append(
                RiskFactor(
                    parameter="Elevated Heat & Humidity",
                    value=f"{heat_idx}°C (Feels like: {effective_temp}°C)",
                    impact="Evaporative cooling is hindered by humidity; fatigue accelerates under direct sunlight.",
                    severity=RiskLevel.MEDIUM
                )
            )
        elif temperature < 10.0:
            score += 15
            factors.append(
                RiskFactor(
                    parameter="Cold Temperature",
                    value=f"{temperature}°C",
                    impact="Cold exposure increases muscle stiffness and risk of hypothermia.",
                    severity=RiskLevel.MEDIUM
                )
            )

        # Wind Evaluation
        if wind_speed >= settings.WIND_GALE_MIN:
            score += 35
            factors.append(
                RiskFactor(
                    parameter="High / Gale Wind",
                    value=f"{wind_speed} m/s (~{round(wind_speed * 3.6)} km/h)",
                    impact="High wind resistance, danger from flying debris, destabilization of lightweight structures.",
                    severity=RiskLevel.HIGH
                )
            )
        elif wind_speed >= settings.WIND_BREEZE_MAX:
            score += 15
            factors.append(
                RiskFactor(
                    parameter="Moderate Wind Breeze",
                    value=f"{wind_speed} m/s (~{round(wind_speed * 3.6)} km/h)",
                    impact="Noticeable buffeting, increased drag for cycling, and drifting of agricultural sprays.",
                    severity=RiskLevel.MEDIUM
                )
            )

        # Precipitation / Storm Evaluation
        if is_thunder:
            score += 45
            factors.append(
                RiskFactor(
                    parameter="Thunderstorm & Lightning Activity",
                    value=condition,
                    impact="Critical threat of cloud-to-ground lightning strikes, localized flash downpours, and sudden violent gusts.",
                    severity=RiskLevel.HIGH
                )
            )
        elif pop >= (settings.RAIN_CHANCE_HIGH / 100.0) or "heavy" in cond_lower:
            score += 25
            factors.append(
                RiskFactor(
                    parameter="High Precipitation Probability",
                    value=f"{int(pop * 100)}% chance ({condition})",
                    impact="Water accumulation, slick road surfaces, muddy fields, and high potential for soaked equipment.",
                    severity=RiskLevel.MEDIUM if pop < 0.85 else RiskLevel.HIGH
                )
            )
        elif pop >= (settings.RAIN_CHANCE_MED / 100.0) or is_rain:
            score += 12
            factors.append(
                RiskFactor(
                    parameter="Scattered Rain / Drizzle",
                    value=f"{int(pop * 100)}% chance ({condition})",
                    impact="Damp conditions, reduced traction, and possible minor disruption to open-air gatherings.",
                    severity=RiskLevel.MEDIUM
                )
            )

        # Visibility Evaluation
        if visibility is not None and visibility < settings.VISIBILITY_POOR:
            score += 20
            factors.append(
                RiskFactor(
                    parameter="Reduced Visibility",
                    value=f"{int(visibility)} meters",
                    impact="Significantly impaired visual range for drivers, cyclists, and equipment operators.",
                    severity=RiskLevel.MEDIUM if visibility > 800 else RiskLevel.HIGH
                )
            )

        # 2. Activity-Specific Multipliers & Advisory Synthesis
        explanation, recommendation = self._generate_activity_advisory(
            activity=activity,
            score=score,
            temperature=temperature,
            effective_temp=effective_temp,
            heat_idx=heat_idx,
            wind_speed=wind_speed,
            pop=pop,
            condition=condition,
            is_thunder=is_thunder,
            is_rain=is_rain,
            is_fog=is_fog,
            factors=factors
        )

        # Determine composite risk level
        if score >= 45 or is_thunder:
            final_risk = RiskLevel.HIGH
        elif score >= 20 or len(factors) > 0:
            final_risk = RiskLevel.MEDIUM
        else:
            final_risk = RiskLevel.LOW
            if not factors:
                factors.append(
                    RiskFactor(
                        parameter="Stable Atmospheric Conditions",
                        value=f"{temperature}°C, {condition}",
                        impact="No significant meteorological stress detected for this activity profile.",
                        severity=RiskLevel.LOW
                    )
                )

        return RiskAnalysisResponse(
            activity=activity.value,
            risk_level=final_risk,
            score=min(100.0, round(score, 1)),
            factors=factors,
            explanation=explanation,
            recommendation=recommendation
        )

    def _generate_activity_advisory(
        self,
        activity: ActivityType,
        score: float,
        temperature: float,
        effective_temp: float,
        heat_idx: float,
        wind_speed: float,
        pop: float,
        condition: str,
        is_thunder: bool,
        is_rain: bool,
        is_fog: bool,
        factors: List[RiskFactor]
    ) -> tuple[str, str]:
        act = activity.value.replace("_", " ").title()

        if is_thunder:
            return (
                f"Severe atmospheric instability detected with {condition}. Conducting {act} outdoors presents an acute lightning and squall hazard.",
                f"Cease outdoor {act} immediately. Seek shelter in a fully enclosed, grounded building or vehicle. Do not stand near isolated tall trees or open bodies of water."
            )

        if activity in [ActivityType.RUNNING, ActivityType.CYCLING]:
            if heat_idx >= settings.HEAT_DANGER_TEMP:
                return (
                    f"Intense thermal stress ({heat_idx}°C heat index) combined with high cardiovascular output in {act} can rapidly trigger heat exhaustion or cramps.",
                    "Postpone intense running/cycling sessions until early morning (before 07:30 AM) or after sunset. If training, reduce intensity by 40% and drink electrolytes every 15 minutes."
                )
            elif is_rain or pop >= 0.5:
                return (
                    f"Rainfall and wet pavements substantially reduce tire and shoe traction while dampening body heat during {act}.",
                    "Use waterproof outer layers, reduce cornering speeds on bicycles, wear high-visibility reflective gear, and avoid painted road markings which become slick."
                )
            elif wind_speed >= settings.WIND_GALE_MIN:
                return (
                    f"High wind gusts (~{round(wind_speed*3.6)} km/h) create unpredictable lateral forces, particularly dangerous on open roads or cross-bridges.",
                    "Stick to sheltered city routes or indoor trainers. Watch for falling tree branches."
                )
            elif score >= 20:
                return (
                    f"Conditions require moderate caution for {act} due to {factors[0].parameter if factors else 'weather factors'}.",
                    "Maintain steady hydration, monitor your heart rate, and carry a water flask."
                )
            else:
                return (
                    f"Atmospheric conditions are optimal for {act}. Clear visibility and mild temperature ({temperature}°C) support comfortable outdoor training.",
                    "Enjoy your workout! Maintain standard hydration and sun protection."
                )

        elif activity == ActivityType.OUTDOOR_EVENT:
            if is_rain or pop >= 0.4:
                return (
                    f"A {int(pop*100)}% chance of precipitation ({condition}) threatens open-air arrangements, electrical setups, and guest comfort.",
                    "Activate secondary rain contingency plans: deploy waterproof canopies, elevate electrical distribution boxes, and prepare dry covered staging."
                )
            elif heat_idx >= 36.0:
                return (
                    f"Elevated temperatures ({temperature}°C, heat index {heat_idx}°C) can cause heat discomfort and fatigue for event attendees and staff.",
                    "Ensure adequate shaded marquees, mist fans, and easily accessible chilled drinking water stations."
                )
            elif wind_speed >= 10.0:
                return (
                    f"Wind speeds exceeding 36 km/h can dislodge temporary marquees, sound banners, and decorative backdrops.",
                    "Anchor all temporary tents and truss systems with certified ballast weights. Lower elevated canvas banners."
                )
            else:
                return (
                    f"Weather is highly favorable for an outdoor event with comfortable temperature ({temperature}°C) and calm winds.",
                    "Proceed with scheduled setup. Standard ventilation and event management will be sufficient."
                )

        elif activity in [ActivityType.FARMING, ActivityType.AGRICULTURE]:
            if is_rain or pop >= 0.6:
                return (
                    f"Anticipated rainfall ({int(pop*100)}% probability) will impact pesticide spraying, soil tilling, and grain harvesting.",
                    "Halt all chemical spraying (fertilizers/pesticides) as rain will wash them away. Ensure drainage channels are cleared to prevent waterlogging in standing crops."
                )
            elif wind_speed >= 8.0:
                return (
                    f"Wind speeds (~{round(wind_speed*3.6)} km/h) will cause significant spray drift during foliar application.",
                    "Postpone chemical crop spraying until wind calms below 10 km/h to prevent pesticide wastage and drift onto neighboring crops."
                )
            elif heat_idx >= 38.0:
                return (
                    f"Severe midday heat accelerates crop evapotranspiration and increases heat exhaustion risk for field laborers.",
                    "Schedule field operations during early morning (6:00 - 10:00 AM). Irrigate crops during evening to minimize evaporative water loss."
                )
            else:
                return (
                    f"Good conditions for regular agricultural activities, weeding, harvesting, and field inspection.",
                    "Normal agricultural operations can proceed smoothly. Plan irrigation according to soil moisture levels."
                )

        elif activity == ActivityType.CONSTRUCTION:
            if wind_speed >= 12.0 or is_rain:
                return (
                    f"Inclement weather (winds {round(wind_speed*3.6)} km/h, precipitation risk) creates hazards for scaffolding, crane operations, and concrete pouring.",
                    "Halt crane lifts and working at height on scaffolding. Cover fresh concrete pours to prevent surface scouring."
                )
            elif heat_idx >= 38.0:
                return (
                    f"Heavy physical labor in {heat_idx}°C heat index poses severe dehydration and heat cramp hazards.",
                    "Mandate regular 15-minute shaded rest breaks every hour. Provide oral rehydration solution (ORS) to site personnel."
                )
            else:
                return (
                    f"Stable construction conditions with manageable temperatures and low precipitation probability.",
                    "Standard site safety and PPE protocols apply. Ideal for concrete curing and structural work."
                )

        elif activity == ActivityType.MARINE_ACTIVITY:
            if wind_speed >= 10.0 or is_thunder:
                return (
                    f"High surface winds ({round(wind_speed*3.6)} km/h) and storm potential cause choppy sea states, elevated wave swell, and surf hazards.",
                    "Fishermen and small vessel operators are strongly advised not to venture into deep sea. Secure coastal crafts in safe harbors."
                )
            else:
                return (
                    f"Gentle sea breeze and calm sea state. Favorable for inshore boating and coastal operations.",
                    "Check daily tidal tables and carry standard life jackets and marine communication radios."
                )

        elif activity == ActivityType.TRAVELLING:
            if is_fog or (factors and any(f.parameter == "Reduced Visibility" for f in factors)):
                return (
                    f"Low visibility conditions ({condition}) create hazard on highways and cause potential flight/train delays.",
                    "Use low-beam headlights and fog lamps. Maintain at least a 4-second following distance behind other vehicles."
                )
            elif is_rain or pop >= 0.5:
                return (
                    f"Rain and wet roads increase vehicle braking distances and cause localized traffic slow-downs.",
                    "Allow 15-20% extra travel time. Check wiper blades and avoid waterlogged underpasses."
                )
            else:
                return (
                    f"Clear highway and transit conditions with good visibility and dry roads.",
                    "Smooth travelling conditions. Have a pleasant journey."
                )

        # Default General Outdoor
        if score >= 45:
            return (
                f"Severe weather conditions present high risk for general outdoor activities ({factors[0].parameter if factors else condition}).",
                "Minimize non-essential outdoor exposure. Stay indoors in secure shelter until conditions stabilize."
            )
        elif score >= 20:
            return (
                f"Current conditions require caution for outdoor activities due to {factors[0].parameter if factors else 'elevated parameters'}.",
                "Take sensible precautions: dress appropriately for the weather, stay hydrated, and keep an eye on sky conditions."
            )
        else:
            return (
                f"The current weather conditions are generally suitable for outdoor activity with mild temperatures and stable skies.",
                "Normal outdoor activity should be reasonable while staying aware of changing conditions."
            )


risk_engine = WeatherImpactIntelligenceEngine()
