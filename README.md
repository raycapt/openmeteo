# Nautical Weather Map — Streamlit + Open-Meteo

This Streamlit app retrieves metocean data (wind, **Significant wave (Hs)**, **wind wave**, swell, currents) from the **Open-Meteo Marine API** for one or many positions/timestamps and visualizes them on a **nautical map** (OpenSeaMap overlay). Bulk CSV/XLSX uploads and **CSV download** are supported.

## Features
- Enter a single **timestamp + lat + lon**, or **upload CSV/XLSX** with multiple rows.
- Fetch weather from **Open-Meteo (marine)** for each point/time.
- Show points on a **nautical map**, **color-coded by wind speed (knots)**:
  - `< 16 kt` = green
  - `16–24 kt` = orange
  - `> 24 kt` = red
- **Hover** to see wind, **Significant wave (Hs)**, **Wind wave**, swell, and current details.
- **Download** the full enriched dataset as CSV.
- Robust timestamp parsing (accepts many formats; auto-corrects common issues).

> ℹ️ Open-Meteo free tier does not require a key. If you have one, set it as `OPENMETEO_API_KEY`.

## Quick Start (Local)
1. **Python 3.10+** recommended.
2. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Add your Open-Meteo API key to **Streamlit secrets**:
   - Create `.streamlit/secrets.toml` (or set env var `OPENMETEO_API_KEY`):
     ```toml
     OPENMETEO_API_KEY = "YOUR_KEY_HERE"
     ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Deploy to Streamlit Cloud
- Push this folder to GitHub, then create a new Streamlit Cloud app pointing to `app.py`.
- On Streamlit Cloud, set the secret **OPENMETEO_API_KEY** under *App → Settings → Secrets* (optional).

## File formats
### Single entry (UI)
- Timestamp (UTC), Latitude, Longitude.

### Bulk CSV/XLSX
Provide columns (case-insensitive; extra columns are kept and passed through):
- `timestamp` — any parseable datetime (assumed UTC if no tz)
- `lat` — latitude
- `lon` — longitude

## Variables & Units
- **Significant wave height (Hs)** → `sigWaveHeight_m` (**meters**).
- **Sig wave direction** → `sigWaveDir_deg_from` (**degrees, coming from**).
- **Wind wave height/direction** → `windWaveHeight_m`, `windWaveDir_deg_from` (meters, degrees coming from).
- **Swell height/direction** → `swellHeight_m`, `swellDir_deg_from` (meters, degrees coming from).
- **Wind speed/direction** → `windSpeed_kt`, `windDir_deg_from` (speed in **knots**, direction **coming from**).
- **Current speed/direction** → `currentSpeed_kt`, `currentDir_deg_to` (speed in **knots**, direction **going to**).

Open-Meteo returns SI units (m/s, m). The app converts speeds to knots.
