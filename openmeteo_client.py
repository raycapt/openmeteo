import requests
from datetime import datetime, timezone
from dateutil import parser as dtparser

__CLIENT_VERSION__ = "4"  # force Streamlit to reload

# Variable families by API:
FORECAST_VARS = {
    "windSpeed": "windspeed_10m",
    "windDirection": "winddirection_10m",
}
MARINE_VARS = {
    "waveHeight": "wave_height",
    "waveDirection": "wave_direction",
    "swellHeight": "swell_wave_height",
    "swellDirection": "swell_wave_direction",
    "windWaveHeight": "wind_wave_height",
    "windWaveDirection": "wind_wave_direction",
}
OCEAN_VARS = {
    "currentSpeed": "current_speed",
    "currentDirection": "current_direction",
}

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL   = "https://marine-api.open-meteo.com/v1/marine"
OCEAN_URL    = "https://ocean-api.open-meteo.com/v1/ocean"


class OpenMeteoClient:
    def __init__(self, api_key: str = None, timeout: int = 20, debug: bool = False):
        self.api_key = api_key  # optional (ignored by OM)
        self.timeout = timeout
        self.debug = debug

    def nearest_hour(self, dtobj: datetime):
        if dtobj.tzinfo is None:
            dtobj = dtobj.replace(tzinfo=timezone.utc)
        else:
            dtobj = dtobj.astimezone(timezone.utc)
        return dtobj.replace(minute=0, second=0, microsecond=0)

    def _get(self, url: str, params: dict):
        if self.api_key:
            params.setdefault("apikey", self.api_key)  # harmless if not used
        if self.debug:
            print(f"DEBUG GET {url}", params)
        r = requests.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _day_params(self, lat: float, lon: float, day_iso: str, hourly_csv: str):
        return {
            "latitude": lat,
            "longitude": lon,
            "hourly": hourly_csv,
            "start_date": day_iso,
            "end_date": day_iso,
            "timezone": "UTC",
            "timeformat": "iso8601",
        }

    def _pick_index(self, times, requested_iso: str):
        if not times:
            return 0
        try:
            t_req = dtparser.isoparse(requested_iso)
        except Exception:
            return 0
        best_i, best_dt = 0, None
        for i, t in enumerate(times):
            try:
                dt = dtparser.isoparse(t)
            except Exception:
                continue
            if best_dt is None or abs((dt - t_req).total_seconds()) < abs((best_dt - t_req).total_seconds()):
                best_dt, best_i = dt, i
        return best_i

    def fetch_point(self, lat: float, lon: float, dtobj: datetime):
        target = self.nearest_hour(dtobj)
        day = target.date().isoformat()
        requested_iso = target.isoformat()

        fc_params = self._day_params(lat, lon, day, ",".join(FORECAST_VARS.values()))
        ma_params = self._day_params(lat, lon, day, ",".join(MARINE_VARS.values()))
        oc_params = self._day_params(lat, lon, day, ",".join(OCEAN_VARS.values()))

        fc_json = ma_json = oc_json = {}
        try:
            fc_json = self._get(FORECAST_URL, fc_params)
        except Exception as e:
            if self.debug: print("WARN forecast fetch:", e)
        try:
            ma_json = self._get(MARINE_URL, ma_params)
        except Exception as e:
            if self.debug: print("WARN marine fetch:", e)
        try:
            oc_json = self._get(OCEAN_URL, oc_params)
        except Exception as e:
            if self.debug: print("WARN ocean fetch:", e)

        return {
            "_requested_iso": requested_iso,
            "_forecast": fc_json,
            "_marine": ma_json,
            "_ocean": oc_json,
        }

    def extract_values(self, payload: dict, requested_iso: str = None):
        requested_iso = requested_iso or payload.get("_requested_iso")
        out = {"iso_time": None}

        # Forecast (wind)
        fc = payload.get("_forecast", {}) or {}
        fc_hourly = fc.get("hourly", {})
        fc_times = fc_hourly.get("time", [])
        if fc_times:
            i = self._pick_index(fc_times, requested_iso)
            out["iso_time"] = out["iso_time"] or fc_times[i]
            for k, v in FORECAST_VARS.items():
                try:
                    out[k] = fc_hourly[v][i]
                except Exception:
                    out[k] = None
        else:
            for k in FORECAST_VARS: out[k] = None

        # Marine (waves)
        ma = payload.get("_marine", {}) or {}
        ma_hourly = ma.get("hourly", {})
        ma_times = ma_hourly.get("time", [])
        if ma_times:
            i = self._pick_index(ma_times, requested_iso)
            out["iso_time"] = out["iso_time"] or ma_times[i]
            for k, v in MARINE_VARS.items():
                try:
                    out[k] = ma_hourly[v][i]
                except Exception:
                    out[k] = None
        else:
            for k in MARINE_VARS: out[k] = None

        # Ocean (currents)
        oc = payload.get("_ocean", {}) or {}
        oc_hourly = oc.get("hourly", {})
        oc_times = oc_hourly.get("time", [])
        if oc_times:
            i = self._pick_index(oc_times, requested_iso)
            out["iso_time"] = out["iso_time"] or oc_times[i]
            for k, v in OCEAN_VARS.items():
                try:
                    out[k] = oc_hourly[v][i]
                except Exception:
                    out[k] = None
        else:
            for k in OCEAN_VARS: out[k] = None

        return out
