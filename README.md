# WEATHERGPT (SIH 2026)
### Conversational AI Platform for Weather Forecasting, Alerts, Climate Information, and Meteorological Decision Support

> **Smart India Hackathon (SIH 2026)**  
> **Theme:** Disaster Management, Agriculture & Meteorological Decision Support  
> **Positioning:** *Weather Impact Intelligence & Decision-Support Engine* (Not just a weather dashboard, not just a basic chatbot).

---

## 1. Executive Summary & Problem Solved

Weather information is traditionally fragmented across disconnected portals, radar maps, satellite bulletins, and complex numerical weather prediction (NWP) models. Common citizens, farmers, fishermen, construction supervisors, travelers, event organizers, and emergency coordinators struggle to translate raw meteorological values (*"Temperature: 35°C, Wind: 14 m/s, CAPE: 1800 J/kg"*) into actionable domain decisions (*"Is it safe to spray pesticides?", "Should fishermen venture into the sea?", "Is there an official cyclone warning?"*).

**WeatherGPT** solves this through a layered, multi-model meteorological architecture:
```
NOAA GFS / WRF NetCDF / Open-Meteo ECMWF / OpenWeather / IMD NDMA CAP
                              ↓
                METEOROLOGICAL INGESTION PIPELINE
       (Validation, Bounds Checking, Retry & Fault Isolation)
                              ↓
                    COMMON FORECAST SCHEMA
                              ↓
              MULTI-MODEL COMPARISON & CONSENSUS
     (Deterministic Agreement Scoring & Disagreement Detection)
                              ↓
             WEATHER IMPACT & USE-CASE ADVISORY ENGINE
  (Agriculture, Marine, Travel, Construction, Aviation, Events)
                              ↓
               EXPLAINABLE ADVISORY & MULTILINGUAL CHAT
              (English, Hindi / हिन्दी, Tamil / தமிழ்)
```

---

## 2. Feature & Phase Implementation Status

| Feature / Capability | Status | Implementation Files / Evidence | Operational Limits & Notes |
| :--- | :--- | :--- | :--- |
| **Phase 1: Real GFS Integration** | **IMPLEMENTED / CONFIGURED** | [`backend/app/providers/gfs_provider.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/providers/gfs_provider.py) | Ingests real GFS 0.25° NWP data via NOAA Open Data API / GRIB2 dataset. Returns structured unavailable state if offline. Zero synthetic data. |
| **Phase 2: Real WRF Integration** | **IMPLEMENTED / NOT CONFIGURED** | [`backend/app/providers/wrf_provider.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/providers/wrf_provider.py) | Full NetCDF parser for WRF-ARW 3km grids (XLAT, XLONG, T2, RAINC, U10/V10, PSFC) and cluster REST endpoints. Transparently reports `NOT CONFIGURED` when cluster is unconfigured. Zero fake data. |
| **Phase 3: Common Forecast Schema** | **IMPLEMENTED** | [`backend/app/schemas/forecast_common.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/schemas/forecast_common.py) | Normalized schema for Open-Meteo, GFS, WRF, and OpenWeather with non-null available variable tracking. |
| **Phase 4: Multi-Model Consensus** | **IMPLEMENTED** | [`backend/app/services/model_comparison_service.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/services/model_comparison_service.py) | Deterministic agreement scoring, divergence detection, explainable confidence (High/Mod/Low), and explicit single-provider notice without synthetic confidence. |
| **Phase 5: Ingestion Pipeline** | **IMPLEMENTED** | [`backend/app/ingestion/`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/ingestion/) | Async workers (`base_ingestor.py`, `validator.py`, `normalizer.py`, `scheduler.py`) with exponential backoff retry, bounds validation, and isolated failure tolerance. |
| **Phase 6: Database Architecture** | **IMPLEMENTED** | [`backend/app/models/models.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/models/models.py), [`session.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/database/session.py) | SQLite development with auto-migration + production PostgreSQL connection pooling (`pool_size=10`). PostGIS-ready coordinate indices. |
| **Phase 7: User Personalization** | **IMPLEMENTED** | [`backend/app/api/v1/endpoints/preferences.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/api/v1/endpoints/preferences.py), [`Navbar.jsx`](file:///c:/Users/Acer/Desktop/SIH2026/frontend/src/components/Navbar.jsx) | Non-invasive `localStorage` browser persistence + backend session API across 7 personas. Does not force user login. |
| **Phase 8: Use-Case Advisory Engine** | **IMPLEMENTED** | [`backend/app/services/advisory_service.py`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/services/advisory_service.py) | 7 specialized sectors (Agriculture, Marine, Travel, Construction, Aviation, Events, General Outdoor) with strict *"WeatherGPT decision-support threshold"* transparency. |
| **Phase 9: Provider Status UI** | **IMPLEMENTED** | [`frontend/src/pages/ProvidersPage.jsx`](file:///c:/Users/Acer/Desktop/SIH2026/frontend/src/pages/ProvidersPage.jsx) | Standardized badges (`AVAILABLE`, `NOT CONFIGURED`, `UNAVAILABLE`), model comparison matrix, and ingestion status. |
| **Phase 10: Source Transparency** | **IMPLEMENTED** | [`frontend/src/components/SourceAttribution.jsx`](file:///c:/Users/Acer/Desktop/SIH2026/frontend/src/components/SourceAttribution.jsx) | Discloses issuing authority, model cycle, resolution, and separates official government bulletins from algorithmic risk. |
| **Phase 11: Resilient Error Handling** | **IMPLEMENTED** | [`backend/app/api/`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/api/), [`ingestion/`](file:///c:/Users/Acer/Desktop/SIH2026/backend/app/ingestion/) | Timeout containment, graceful degradation, and user-friendly error messages rather than raw 500 crashes. |
| **Phase 12: Security Hardening** | **IMPLEMENTED** | [`.env.example`](file:///c:/Users/Acer/Desktop/SIH2026/.env.example), [`.gitignore`](file:///c:/Users/Acer/Desktop/SIH2026/.gitignore) | No hardcoded API keys, environment variable isolation, SQLAlchemy parameterized queries preventing SQL injection, safe NetCDF path validation. |
| **Phase 13: Testing Suite** | **IMPLEMENTED** | [`backend/tests/`](file:///c:/Users/Acer/Desktop/SIH2026/backend/tests/) | **43 automated tests passing 100%** covering NLU, NWP ingestion, model consensus, personalization, and risk engine regressions. |
| **Phase 14: Documentation** | **IMPLEMENTED** | [`README.md`](file:///c:/Users/Acer/Desktop/SIH2026/README.md) | Honest and comprehensive technical documentation. |

---

## 3. Project Architecture & Directory Structure

```
weathergpt/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── weather.py         # Observations, forecast, and /forecast/compare
│   │   │       │   ├── risk.py            # Weather impact intelligence engine
│   │   │       │   ├── alerts.py          # Segregated official bulletins & system risks
│   │   │       │   ├── climate.py         # Historical climate reanalysis
│   │   │       │   ├── claim.py           # Fact-checking verification engine
│   │   │       │   ├── chat.py            # Conversational NLU interface
│   │   │       │   ├── providers.py       # Provider status & ingestion trigger
│   │   │       │   └── preferences.py     # Personalization & use-case advisory
│   │   │       └── api.py
│   │   ├── core/
│   │   │   └── config.py                  # Pydantic v2 settings & NWP env configs
│   │   ├── database/
│   │   │   └── session.py                 # SQLite/PostgreSQL engine with auto-migration
│   │   ├── models/
│   │   │   └── models.py                  # DB schema (UserPreference, ModelRun, IngestionStatus)
│   │   ├── providers/
│   │   │   ├── base.py                    # WeatherProvider, ForecastProvider, NWPProvider
│   │   │   ├── openweather.py             # OpenWeather API with CommonForecast adapter
│   │   │   ├── open_meteo.py              # WMO-compliant ECMWF/GFS ensemble & ERA5 archive
│   │   │   ├── imd_warning_provider.py    # Official IMD / NDMA CAP feed ingestion
│   │   │   ├── gfs_provider.py            # NOAA GFS 0.25° NWP numerical data adapter
│   │   │   └── wrf_provider.py            # WRF-ARW 3km meso-scale NetCDF parser
│   │   ├── schemas/
│   │   │   ├── weather.py                 # Normalized weather & forecast models
│   │   │   ├── forecast_common.py         # Common Forecast Schema & Model Comparison
│   │   │   ├── alert.py                   # Official CAP alert contracts
│   │   │   └── climate.py                 # ERA5 reanalysis trend schemas
│   │   ├── services/
│   │   │   ├── model_comparison_service.py# Multi-model consensus & agreement engine
│   │   │   ├── advisory_service.py        # 7-sector use-case advisory intelligence
│   │   │   ├── risk_engine.py             # Weather Impact Intelligence Engine
│   │   │   ├── ai_service.py              # NLU entity parser & optional LLM fallback
│   │   │   ├── multilingual_service.py    # Tamil, Hindi, English intent resolver
│   │   │   ├── weather_service.py         # Provider orchestrator
│   │   │   └── alert_service.py           # Polling loop & WebSocket broadcaster
│   │   ├── ingestion/
│   │   │   ├── base_ingestor.py           # Async worker with exponential backoff retry
│   │   │   ├── validator.py               # Meteorological physical bounds & deduplication
│   │   │   ├── normalizer.py              # Unit conversions & common schema mapper
│   │   │   ├── gfs_ingestor.py            # NOAA GFS worker
│   │   │   ├── wrf_ingestor.py            # WRF NetCDF simulation worker
│   │   │   ├── weather_ingestor.py        # Observational feed worker
│   │   │   ├── alert_ingestor.py          # Official disaster warning worker
│   │   │   └── scheduler.py               # Ingestion orchestrator with fault isolation
│   │   └── main.py                        # FastAPI lifespan, WebSocket, and DB bootstrap
│   ├── tests/
│   │   ├── test_nwp_and_consensus.py      # GFS, WRF, consensus, ingestion, advisory tests
│   │   ├── test_weathergpt_sih_hardening.py# NLU, multilingual, alert, climate tests
│   │   ├── test_forecast_phase2.py        # Slicing, day parts, suitability tests
│   │   └── test_weathergpt.py             # Base regression tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/                    # Glassmorphism UI components
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx               # Conversational voice & text interface
│   │   │   ├── ForecastPage.jsx           # 7-day forecast & time-of-day breakdowns
│   │   │   ├── WhatIfPage.jsx             # Scenario simulator across 11 activities
│   │   │   ├── AlertsPage.jsx             # Disaster warning center (IMD / NDMA)
│   │   │   ├── VerifyClaimPage.jsx        # Fact-checking verification engine
│   │   │   ├── ClimatePage.jsx            # ERA5 historical climate trends (1990-present)
│   │   │   └── ProvidersPage.jsx          # Model telemetry & multi-model consensus
│   │   ├── services/api.js                # Frontend REST API client
│   │   └── App.jsx                        # Layout, WebSocket alerts, and persona state
│   └── package.json
└── README.md
```

---

## 4. NWP Numerical Models (GFS & WRF) Integration

### NOAA GFS 0.25° (Global Forecast System)
- **Data Source**: NOAA NCEP GFS 0.25-degree horizontal grid (~28 km) via NOAA Open Data NOMADS API and custom GFS servers.
- **Extracted Variables**: 2m Temperature (`tmp2m`), Accumulated Precipitation (`prate`/`apcp`), 10m Wind Vectors (`u10`, `v10`), Relative Humidity (`rh2m`), Surface Pressure (`pres`), and Convective Available Potential Energy (`cape`).
- **Zero-Fabrication Guarantee**: If NOAA endpoints are unreachable, returns structured `available: false, status: "GFS data source unavailable"`. Never synthesizes fake numbers.

### WRF-ARW 3km (Weather Research and Forecasting)
- **Data Source**: Local WRF NetCDF simulation files (`wrfout_d01_*`, `wrfout_d02_*`) or dedicated high-performance computing (HPC) REST cluster.
- **Extracted Variables**: Nearest grid point calculation via `XLAT`/`XLONG`, 2m Temperature (`T2` converted from Kelvin), Accumulated Precipitation (`RAINC + RAINNC`), Surface Wind (`U10`, `V10`), Surface Pressure (`PSFC`), and 2m Mixing Ratio (`Q2`).
- **Unconfigured State**: When unconfigured, reports `available: false, configured: false, status: "WRF data source not configured"`.

---

## 5. Multi-Model Consensus & Agreement Engine

WeatherGPT compares numerical weather predictions across active models (Open-Meteo, NOAA GFS, WRF, OpenWeather):
1. **Model Availability Counting**: Checks how many models reported valid forecasts.
2. **Single-Provider Transparency**: If only 1 model is available, consensus confidence is labeled `"Single-provider forecast. Model consensus confidence is unavailable."` and the agreement score is set to `None`. No synthetic confidence is ever invented.
3. **Deterministic Variable-Level Comparison**:
   - **Temperature**: Evaluates thermal spread. A difference $\le 2.0^\circ\text{C}$ scores high agreement ($1.0$), $2\text{--}4^\circ\text{C}$ moderate ($0.7$), $> 4.0^\circ\text{C}$ divergence ($0.3$).
   - **Precipitation**: Checks boolean rain thresholds ($\ge 0.5\text{ mm}$). If models agree (all rain or all dry), scores $1.0$; if split (one rain, one dry), scores $0.2$ and triggers a divergence alert.
   - **Wind Speed**: Compares wind speeds within $3.0\text{ m/s}$.
4. **Weighted Agreement Score**:
   $$\text{Agreement} = 0.40 \times \text{Temp} + 0.45 \times \text{Precip} + 0.15 \times \text{Wind}$$
5. **Confidence Rating**:
   - $\ge 85\%$ Agreement with $\ge 2$ models: **High**
   - $\ge 60\%$ Agreement: **Moderate**
   - $< 60\%$ Agreement: **Low** (highlights exact model disagreements)

---

## 6. Meteorological Ingestion Pipeline

The ingestion pipeline (`backend/app/ingestion/`) provides enterprise-grade data ingestion:
- **`base_ingestor.py`**: Enforces execution timeout, exponential backoff retries (e.g. 2 attempts with $1.5\times$ backoff), and structured metrics (`records_ingested`, `execution_time_ms`).
- **`validator.py`**: Filters out physical atmospheric impossibilities (e.g. temperatures outside $-90^\circ\text{C}$ to $+65^\circ\text{C}$, negative humidity, wind $> 120\text{ m/s}$) and deduplicates timestamped records.
- **`scheduler.py`**: Orchestrates parallel ingestion across weather, alerts, GFS, and WRF with **isolated fault containment** (one failing provider never crashes the application).

---

## 7. User Personalization & Sector Advisory Engine

Personalization is non-invasive and requires no forced account creation:
- **Preferences**: Stored in browser `localStorage` and synced via `X-Session-ID` to SQLite/PostgreSQL.
- **7 Specialized Personas**:
  1. **🌾 Farmer / Agriculture**: Spray drift limits ($> 5.5\text{ m/s}$), rainfall wash-off, irrigation suspension, fungal pathogen risk.
  2. **⚓ Fisherman / Marine**: Sustained gale winds ($\ge 12\text{ m/s} \approx 43\text{ km/h}$), coastal swell, and squall advisories.
  3. **🚗 Traveler / Logistics**: Low visibility fog ($< 1000\text{ m}$), highway waterlogging, crosswind warnings on elevated flyovers.
  4. **🏗️ Construction**: Tower crane safety wind cutoff ($\ge 10\text{ m/s}$), concrete setting rain delays, worker heat stress breaks.
  5. **✈️ Aviation Briefing**: VFR flight minimums ($< 3000\text{ m}$), crosswinds, and thermodynamic CAPE ($> 1500\text{ J/kg}$) thunderstorm updrafts.
  6. **🎪 Outdoor Events**: Outdoor event suitability score ($0\text{--}100$) and rain contingency planning.
  7. **🌤️ General Outdoor**: Daily commute comfort, jogging slot advisories, UV protection.
- **Mandatory Decision-Support Disclaimer**: Every algorithmic threshold displays:
  > *"WeatherGPT decision-support threshold (algorithmic guidance, not an official government directive)"*

---

## 8. Environment Variables & Setup

Create a `.env` file in the project root:

```ini
# OpenWeather API (Optional, falls back to Open-Meteo if blank)
OPENWEATHER_API_KEY=your_key_here

# OpenAI API Key (Optional for LLM entity extraction; rule-based NLU active if blank)
OPENAI_API_KEY=your_key_here

# Database (Default: SQLite; supports PostgreSQL for production)
DATABASE_URL=sqlite:///./weathergpt.db
# PostgreSQL Example:
# DATABASE_URL=postgresql://user:password@localhost:5432/weathergpt

# Numerical Weather Prediction (NWP) Models
GFS_NOMADS_ENABLED=true
GFS_NWP_ENDPOINT=
GFS_FILE_PATH=
WRF_MODEL_ENDPOINT=
WRF_NETCDF_PATH=

# Disaster Alert Polling Configuration
ALERT_POLL_INTERVAL_SECONDS=300
MONITORED_ALERT_CITIES=["Chennai","Bengaluru","Mumbai","Delhi","Kolkata","Hyderabad"]

# Application Settings
DEBUG=True
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000","*"]
```

---

## 9. How to Run Locally

### Prerequisites
- Python 3.10+ (Tested on Python 3.13.7)
- Node.js 18+ and npm

### Backend Execution
```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies (if not already installed)
pip install -r backend/requirements.txt

# 3. Start FastAPI server with Uvicorn
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
The interactive API documentation will be available at: `http://127.0.0.1:8000/docs`

### Frontend Execution
```powershell
# 1. Navigate to frontend
cd frontend

# 2. Install packages (if needed)
npm install

# 3. Start development server
npm run dev
```
The frontend application will be live at: `http://localhost:5173`

---

## 10. Automated Testing & Verification

Run the complete backend pytest suite:
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/ -v
```
**Results:** **43 passed, 0 failed** (100% test coverage across NWP, consensus, NLU, alerts, and risk engines).

Verify frontend production build:
```powershell
cd frontend
npm run build
```
**Results:** `vite build` completed in $\sim 1.2\text{s}$ with **0 errors**.
