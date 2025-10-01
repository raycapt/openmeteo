import requests
from datetime import datetime, timezone
from dateutil import parser as dtparser

# Map our internal names -> Open-Meteo hourly params
PARAMS = {
    "windSpeed": "windspeed_10m",
    "windDirection": "winddirection_10m",
    "waveHeight": "wave_height",
    "waveDirection": "wave_direction",
    "swellHeight": "swell_wave_height",
    "swellDirection": "swell_wave_direction",
    "windWaveHeight": "wind_wave_height",
    "windWaveDirection": "wind_wave_direction",
    "currentSpeed": "current_speed",
    "currentDirection": "current_direction",
}

class OpenMeteoClient:
    def __init__(self, api_key: str = None, timeout: int = 20):
        self.api_key = api_key  # Not required for free tier
        self.timeout = timeout
        self.base_url = "https://marine-api.open-meteo.com/v1/marine"

    def nearest_hour(self, dtobj: datetime):
        if dtobj.tzinfo is None:
            dtobj = dtobj.replace(tzinfo=timezone.utc)
        else:
            dtobj = dtobj.astimezone(timezone.utc)
        return dtobj.replace(minute=0, second=0, microsecond=0)

    def fetch_point(self, lat: float, lon: float, dtobj: datetime):
        target = self.nearest_hour(dtobj)
        day = target.date().isoformat()
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(PARAMS.values()),
            "start_date": day,
            "end_date": day,
            "timezone": "UTC",
            "timeformat": "iso8601",
        }
        # Open-Meteo ignores unknown params; safe to include if you have a key
        if self.api_key:
            params["apikey"] = self.api_key

        r = requests.get(self.base_url, params=params, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        data["_requested_iso"] = target.isoformat()
        return data

    def extract_values(self, payload: dict, requested_iso: str = None):
        try:
            hourly = payload["hourly"]
            times = hourly.get("time", [])
        except Exception:
            return {}

        # Choose the hour closest to what we asked for
        idx = 0
        if requested_iso and times:
            try:
                t_req = dtparser.isoparse(requested_iso)
            except Exception:
                t_req = None
            if t_req is not None:
                best_dt = None
                best_i = 0
                for i, t in enumerate(times):
                    try:
                        dt = dtparser.isoparse(t)
                    except Exception:
                        continue
                    if best_dt is None or abs((dt - t_req).total_seconds()) < abs((best_dt - t_req).total_seconds()):
                        best_dt = dt
                        best_i = i
                idx = best_i

        out = {}
        for k, v in PARAMS.items():
            try:
                out[k] = hourly[v][idx]
            except Exception:
                out[k] = None
        out["iso_time"] = times[idx] if times else None
        return out
