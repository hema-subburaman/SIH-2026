# WEATHERGPT (SIH 2026)
### Conversational AI Platform for Weather Forecasting, Alerts, Climate Information and Decision Support

> **Smart India Hackathon (SIH 2026)**  
> **Theme:** Disaster Management, Agriculture & Meteorological Decision Support  
> **Positioning:** *Weather Impact Intelligence & Decision-Support Engine* (Not just a weather dashboard, not just a basic chatbot).

---

## 1. Executive Summary & Problem Solved

Weather information is fragmented across disconnected portals, radar maps, satellite bulletins, and numerical forecast models. Common citizens, farmers, event organizers, emergency workers, and logistics teams struggle to translate raw metrics (*"Temperature: 35°C, Wind: 14 m/s"*) into actionable daily decisions (*"Is it safe to run?", "Will rain wash away fertilizer sprays?", "Is there an official cyclone warning?"*).

**WeatherGPT** bridges this divide by implementing the **Weather Impact Intelligence Engine**:
```
RAW WEATHER DATA (OpenWeather / Open-Meteo / IMD)
       ↓
CONTEXT & ENTITY EXTRACTION (Activity, Time, Location)
       ↓
WEATHER IMPACT INTELLIGENCE ENGINE
       ↓
COMPOSITE RISK LEVEL (LOW / MEDIUM / HIGH)
       ↓
EXPLAINABLE FACTORS & WHY IT MATTERS
       ↓
ACTIONABLE ACTIVITY ADVISORY & MULTILINGUAL CONVERSATION
```

---

## 2. Core Modules & Innovations

1. **Weather Impact Intelligence Engine (`risk_engine.py`)**:
   - Converts temperature, heat index, wind chill, precipitation rate, and gusts into explainable risk ratings (LOW / MEDIUM / HIGH).
   - Tailored tolerance models across **11 distinct activities**: Running, Walking, Cycling, Outdoor Events, Travelling, Farming, Agriculture/Irrigation, Construction, Marine/Fishing, Aviation Briefing, and General Outdoor.
   - Distinct disclaimers that prototype thresholds are advisory and not official medical/meteorological standards.

2. **Layered Provider Pattern & NWP Integration (`providers/`)**:
   - Normalized provider interfaces: `WeatherProvider`, `ForecastProvider`, `WarningProvider`, `NWPProvider`.
   - **OpenWeather API**: Real-time observations and 5-day forecasts via `OPENWEATHER_API_KEY`.
   - **Open-Meteo Service**: WMO-compliant high-resolution fallback that operates with zero keys and zero fabrication.
   - **GFS & WRF NWP Model Interfaces**: Real NOAA GFS (0.25°) and WRF (3 km meso-scale) pipeline hooks that transparently display *"Provider not configured"* when HPC clusters are offline, strictly adhering to zero-fake-data rules.

3. **Disaster Early Warning Center (`AlertsPage.jsx`)**:
   - Ingests CAP bulletins from the India Meteorological Department (IMD) / NDMA Sachet feeds.
   - **Strict Segregation**: Visually and architecturally isolates `OFFICIAL GOVERNMENT WARNING` bulletins from algorithmic `SYSTEM WEATHER RISKS`.

4. **Fact-Checking & Claim Verifier (`VerifyClaimPage.jsx`)**:
   - Verifies citizen claims and social media rumors against active telemetry.
   - Returns `VERIFIED`, `CONTRADICTED`, or `UNVERIFIED`.
   - Per SIH safety requirements, any cyclone or disaster claim without corroborated official bulletins is strictly tagged `UNVERIFIED`.

5. **Climate & Decadal Trend Analytics (`ClimatePage.jsx`)**:
   - Visualizes multi-year historical ERA5 reanalysis data (1990 - present).
   - Interactive charts of temperature curves, decadal warming rates, and precipitation shifts. Explicitly separated from predictive forecasts.

6. **Multilingual & Voice Interface (`services/voiceService.js`)**:
   - Supports **English**, **Hindi (हिन्दी)**, and **Tamil (தமிழ்)** with automatic script/phonetic detection.
   - Browser-native Web Speech STT (Speech-to-Text) and TTS (Text-to-Speech) using `en-IN`, `hi-IN`, and `ta-IN` locales.

---

## 3. Project Architecture & Repository Structure

```
weathergpt/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── weather.py     # Real-time & forecast telemetry
│   │   │       │   ├── risk.py        # Weather impact intelligence engine
│   │   │       │   ├── alerts.py      # Segregated official & system alerts
│   │   │       │   ├── climate.py     # Historical climate reanalysis
│   │   │       │   ├── claim.py       # Fact-checking verification engine
│   │   │       │   ├── chat.py        # Conversational NLU interface
│   │   │       │   └── providers.py   # NWP & provider telemetry
│   │   │       └── api.py
│   │   ├── core/
│   │   │   └── config.py              # Pydantic settings & threshold config
│   │   ├── database/
│   │   │   └── session.py             # SQLAlchemy session & SQLite/Postgres
│   │   ├── models/
│   │   │   └── models.py              # DB schema (Users, Alerts, Obs, Forecasts)
│   │   ├── providers/
│   │   │   ├── base.py                # Abstract provider interfaces
│   │   │   ├── openweather.py         # OpenWeather API integration
│   │   │   ├── open_meteo.py          # WMO-compliant real-time & climate provider
│   │   │   ├── imd_warning_provider.py# IMD / NDMA CAP feed ingestion
│   │   │   ├── gfs_provider.py        # NOAA GFS NWP model hook
│   │   │   └── wrf_provider.py        # Meso-scale WRF model hook
│   │   ├── schemas/                   # Pydantic v2 validation contracts
│   │   ├── services/
│   │   │   ├── risk_engine.py         # Weather Impact Intelligence Engine
│   │   │   ├── ai_service.py          # NLU entity parser & LLM layer
│   │   │   ├── multilingual_service.py# Tamil, Hindi, English translation
│   │   │   ├── weather_service.py     # Provider orchestrator & normalizer
│   │   │   ├── alert_service.py       # Alert manager & WebSocket broadcaster
│   │   │   ├── climate_service.py     # Climate reanalysis analytics
│   │   │   └── claim_verifier.py      # Telemetry fact-checking engine
│   │   └── main.py                    # FastAPI entrypoint, CORS, WebSockets
│   ├── tests/
│   │   └── test_weathergpt.py         # Pytest test suite (100% passing)
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx             # Search, geolocation, language toggle
│   │   │   ├── CurrentWeatherCard.jsx # Normalized hero & intelligence preview
│   │   │   ├── RiskBadge.jsx          # LOW/MED/HIGH visual indicators
│   │   │   ├── ExplainableFactors.jsx # Factor impact breakdown & advice
│   │   │   ├── SourceAttribution.jsx  # Strict source citations on every card
│   │   │   └── VoiceButton.jsx        # Web Speech API STT/TTS button
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx           # Conversational assistant & voice Q&A
│   │   │   ├── ForecastPage.jsx       # 7-day cards & hourly temperature curves
│   │   │   ├── WhatIfPage.jsx         # Interactive activity impact simulator
│   │   │   ├── AlertsPage.jsx         # Disaster warning center (IMD vs System)
│   │   │   ├── VerifyClaimPage.jsx    # Fact-checking claim verification
│   │   │   ├── ClimatePage.jsx        # Multi-year historical climate analytics
│   │   │   └── ProvidersPage.jsx      # NWP GFS/WRF & operational statuses
│   │   ├── services/
│   │   │   ├── api.js                 # REST client
│   │   │   └── voiceService.js        # Browser speech recognition & synthesis
│   │   ├── utils/
│   │   │   └── constants.js           # Translations, presets, activities
│   │   ├── App.jsx                    # Root state & responsive layout
│   │   ├── index.css                  # Atmospheric glassmorphic design system
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js                 # Vite configuration with backend proxy
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Getting Started Locally

### Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** & **npm**

### Step 1: Clone and Configure Environment
```bash
git clone <repository_url>
cd SIH2026

# Copy environment template
cp .env.example .env
```
*(Optional: add your `OPENWEATHER_API_KEY` and `OPENAI_API_KEY` in `.env`. If left empty, WeatherGPT automatically utilizes the WMO-compliant Open-Meteo meteorological feed and native rule-based NLU without breaking).*

### Step 2: Start the FastAPI Backend
```bash
# In project root:
# If using virtual environment:
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

pip install -r backend/requirements.txt

# Run backend server
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend API Docs will be live at `http://127.0.0.1:8000/docs`.*

### Step 3: Start the React Frontend
```bash
# In a new terminal:
cd frontend
npm install
npm run dev
```
*Frontend will be running at `http://localhost:5173`.*

---

## 5. Running Automated Backend Tests

Verify the Weather Impact Intelligence Engine, NLU entity parsing, multilingual detection, and claim verifier:
```bash
$env:PYTHONPATH="backend"
pytest backend/tests/ -v
```
All 6 core verification test cases will execute and pass.

---

## 6. Docker Deployment

Deploy the full stack in isolated containers:
```bash
docker-compose up --build -d
```
- Frontend: `http://localhost:80`
- Backend API: `http://localhost:8000`

---

## 7. Step-by-Step SIH Demonstration Flow for Judges

1. **Real-Time Weather Ingestion & Location Autocomplete**:
   - Type *"Chennai"*, *"Delhi"*, or *"Mumbai"* in the search box or click quick city preset pills.
   - Observe real-time temperature, feels-like, wind, humidity, pressure, and visibility.
   - Point out the **Source Attribution** tag: *"Source: Open-Meteo Public Meteorological Service (WMO Compliant)"* or *"Source: OpenWeather"*.

2. **Forecast Inquiry**:
   - Ask: *"Will it rain tomorrow?"* in the Chat Assistant.
   - Observe how the NLU identifies `intent=rain_inquiry`, `target_date=tomorrow`, checks numerical forecast precipitation probabilities, and answers with rain chance % and umbrella recommendation.

3. **Weather Impact Intelligence Engine in Action**:
   - Ask: *"Can I go running tomorrow evening?"*
   - Observe the structured decision output:
     - **Risk Badge**: `MEDIUM RISK` / `HIGH RISK`
     - **Explainable Factors**: Identifies elevated heat index, humidity, or precipitation.
     - **Why?**: Explains cardiovascular strain and dehydration hazard under current conditions.
     - **Actionable Recommendation**: Suggests early morning workout before 07:30 AM and hydration pacing.

4. **What-If Scenario Simulator**:
   - Navigate to the **What-If** tab.
   - Select activity: *"Marine / Coastal Fishing"*. Adjust wind slider to 16 m/s.
   - Notice the engine instantly recalculates to `HIGH RISK`, citing squally seas, wave swell, and advising boaters not to venture into deep sea.

5. **Disaster Early Warning Protocol**:
   - Navigate to the **Alerts Center**.
   - Note the strict architectural segregation between **Official Government Warnings (IMD)** and **System Weather Risks**.
   - Click *"Simulate IMD CAP Bulletin (Judge Demo)"* to demonstrate real-time CAP bulletin ingestion and emergency instruction display.

6. **Multilingual Capability**:
   - Toggle language to **தமிழ் (Tamil)** in the top bar.
   - Ask: *"Naalaikku mazha varuma?"*
   - Observe the response generated entirely in natural Tamil with localized weather factors and recommendations.
   - Toggle language to **हिन्दी (Hindi)** and ask: *"Kya kal barish hogi?"* to show Hindi support.

7. **Voice Accessibility**:
   - Click the **[🎤 Speak]** button on the input bar.
   - Speak your question; watch the speech-to-text transcript populate and trigger the intelligence engine.
   - Click the audio speaker icon on any assistant answer to hear the response read aloud via Text-to-Speech.

8. **Fact-Checking & Claim Verification**:
   - Navigate to the **Verify Claim** tab.
   - Test: *"There is a cyclone warning in Chennai right now"*.
   - The platform checks the official IMD warning archive. Since no active cyclone warning exists, it strictly outputs **UNVERIFIED**, demonstrating responsible AI that rejects false rumors.

9. **Historical Climate Trend Analytics**:
   - Navigate to the **Climate Trends** tab.
   - Review the 10-to-20 year ERA5 reanalysis curve, baseline mean, decadal warming trend (+0.35°C/decade), and observational summary.

10. **NWP / GFS / WRF Architectural Transparency**:
    - Navigate to the **NWP & Providers** tab.
    - Show judges the provider contracts: OpenWeather, Open-Meteo, IMD Warning Provider, GFS (0.25°), and WRF (3 km).
    - Note that unconfigured NWP models transparently display *"Provider not configured"* with zero fabricated runs.

---

## 8. REST API Documentation Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/weather/current` | Retrieves normalized current observations |
| `GET` | `/api/v1/weather/forecast` | Retrieves 5-to-7 day numerical forecast intervals |
| `GET` | `/api/v1/weather/location` | Location search and coordinate autocomplete |
| `POST` | `/api/v1/risk/analyze` | Weather Impact Intelligence Engine evaluation |
| `GET` | `/api/v1/alerts` | Segregated official IMD warnings and system risks |
| `GET` | `/api/v1/climate/history` | Historical climate observations and anomaly trends |
| `POST` | `/api/v1/claim/verify` | Telemetry fact-checking for weather rumors |
| `POST` | `/api/v1/chat/query` | Conversational NLU query processor |
| `GET` | `/api/v1/providers/status` | Operational status of all meteorological & NWP providers |
| `WS` | `/ws/alerts` | Real-time WebSocket feed for emergency bulletins |

---

## 9. License & Team Acknowledgement

Developed for the **Smart India Hackathon (SIH 2026)**. Built in compliance with all problem requirements, strict meteorological attribution standards, and accessibility guidelines.
