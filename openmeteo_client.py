
import math
import requests
from datetime import datetime, timezone
from dateutil import parser as dtparser

__CLIENT_VERSION__ = "5.4"  # dual Ocean request (speed/dir -> fallback to u/v)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL   = "https://marine-api.open-meteo.com/v1/marine"
OCEAN_URL    = "https://ocean-api.open-meteo.com/v1/ocean"

class OpenMeteoClient:
    def __init__(self, api_key: str = None, timeout: int = 20, debug: bool = False):
        self.api_key = api_key
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
            params.setdefault("apikey", self.api_key)
        req = requests.Request("GET", url, params=params).prepare()
        if self.debug:
            print("DEBUG GET", req.url)
        with requests.Session() as s:
            r = s.send(req, timeout=self.timeout)
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
            t_req = dtparser.isoparse(requested_iso) if requested_iso else None
        except Exception:
            t_req = None
        if t_req is None:
            return 0
        if t_req.tzinfo is None:
            t_req = t_req.replace(tzinfo=timezone.utc)

        best_i, best_dt = 0, None
        for i, t in enumerate(times):
            try:
                dt = dtparser.isoparse(t)
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if best_dt is None or abs((dt - t_req).total_seconds()) < abs((best_dt - t_req).total_seconds()):
                best_dt, best_i = dt, i
        return best_i

    def _uv_to_speed_dir(self, u, v):
        try:
            uu = float(u); vv = float(v)
        except Exception:
            return None, None
        spd = math.hypot(uu, vv)
        bearing = (math.degrees(math.atan2(uu, vv)) + 360.0) % 360.0
        return spd, bearing

    def fetch_point(self, lat: float, lon: float, dtobj: datetime):
        target = self.nearest_hour(dtobj)
        day = target.date().isoformat()
        requested_iso = target.isoformat()

        fc_params = self._day_params(lat, lon, day, "windspeed_10m,winddirection_10m")
        fc_params["windspeed_unit"] = "kn"

        ma_params = self._day_params(
            lat, lon, day,
            "wave_height,wave_direction,swell_wave_height,swell_wave_direction,wind_wave_height,wind_wave_direction"
        )

        oc_params_1 = self._day_params(lat, lon, day, "current_speed,current_direction")
        oc_params_2 = self._day_params(lat, lon, day, "current_u,current_v")

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
            oc_json = self._get(OCEAN_URL, oc_params_1)
            h = oc_json.get("hourly", {}) if isinstance(oc_json, dict) else {}
            if not h or ("current_speed" not in h and "current_direction" not in h):
                raise ValueError("Ocean response missing current_speed/current_direction; retrying u/v")
        except Exception as e:
            if self.debug: print("INFO ocean retry using u/v:", e)
            try:
                oc_json = self._get(OCEAN_URL, oc_params_2)
            except Exception as e2:
                if self.debug: print("WARN ocean u/v fetch:", e2)
                oc_json = {}

        return {
            "_requested_iso": requested_iso,
            "_forecast": fc_json,
            "_marine": ma_json,
            "_ocean": oc_json,
            "_units": {"wind": "kn", "current": "mps"},
        }

    def extract_values(self, payload: dict, requested_iso: str = None):
        requested_iso = requested_iso or payload.get("_requested_iso")
        out = {"iso_time": None}

        fc = payload.get("_forecast", {}) or {}
        fc_hourly = fc.get("hourly", {})
        fc_times = fc_hourly.get("time", [])
        if fc_times:
            i = self._pick_index(fc_times, requested_iso)
            out["iso_time"] = out["iso_time"] or fc_times[i]
            out["windSpeed"]     = fc_hourly.get("windspeed_10m",    [None])[i] if "windspeed_10m"    in fc_hourly else None
            out["windDirection"] = fc_hourly.get("winddirection_10m",[None])[i] if "winddirection_10m" in fc_hourly else None
        else:
            out["windSpeed"] = None
            out["windDirection"] = None

        ma = payload.get("_marine", {}) or {}
        ma_hourly = ma.get("hourly", {})
        ma_times = ma_hourly.get("time", [])
        if ma_times:
            i = self._pick_index(ma_times, requested_iso)
            out["iso_time"] = out["iso_time"] or ma_times[i]
            def get(h, k):
                try: return h.get(k, [None])[i]
                except Exception: return None
            out["waveHeight"]        = get(ma_hourly, "wave_height")
            out["waveDirection"]     = get(ma_hourly, "wave_direction")
            out["swellHeight"]       = get(ma_hourly, "swell_wave_height")
            out["swellDirection"]    = get(ma_hourly, "swell_wave_direction")
            out["windWaveHeight"]    = get(ma_hourly, "wind_wave_height")
            out["windWaveDirection"] = get(ma_hourly, "wind_wave_direction")
        else:
            for k in ["waveHeight","waveDirection","swellHeight","swellDirection","windWaveHeight","windWaveDirection"]:
                out[k] = None

        oc = payload.get("_ocean", {}) or {}
        oc_hourly = oc.get("hourly", {})
        oc_times = oc_hourly.get("time", [])
        if oc_times:
            i = self._pick_index(oc_times, requested_iso)
            out["iso_time"] = out["iso_time"] or oc_times[i]

            speed = oc_hourly.get("current_speed",     [None])[i] if "current_speed"     in oc_hourly else None
            direction = oc_hourly.get("current_direction",[None])[i] if "current_direction" in oc_hourly else None

            if speed is None or direction is None:
                if speed is None and "current" in oc_hourly:
                    try: speed = oc_hourly["current"][i]
                    except Exception: pass
                u = oc_hourly.get("current_u", [None])[i] if "current_u" in oc_hourly else None
                v = oc_hourly.get("current_v", [None])[i] if "current_v" in oc_hourly else None
                if (u is not None) and (v is not None):
                    spd, bear = self._uv_to_speed_dir(u, v)
                    if speed is None: speed = spd
                    if direction is None: direction = bear

            out["currentSpeed"] = speed
            out["currentDirection"] = direction
        else:
            out["currentSpeed"] = None
            out["currentDirection"] = None

        return out
