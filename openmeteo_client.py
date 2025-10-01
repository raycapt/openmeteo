import requests
from datetime import datetime, timezone

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
        ts = self.nearest_hour(dtobj).isoformat()
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(PARAMS.values()),
            "start": ts,
            "end": ts,
        }
        if self.api_key:
            params["apikey"] = self.api_key

        r = requests.get(self.base_url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def extract_values(self, payload: dict):
        try:
            hourly = payload["hourly"]
        except Exception:
            return {}
        out = {}
        for k, v in PARAMS.items():
            try:
                out[k] = hourly[v][0]
            except Exception:
                out[k] = None
        out["iso_time"] = hourly.get("time", [None])[0]
        return out
