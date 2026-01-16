from __future__ import annotations

from typing import Dict, Any, List
from pathlib import Path
import json

import fastf1
import pandas as pd


TEI_CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "processed" / "tei"


def load_weather_and_tei(season: int, round: int, session_name: str) -> Dict[str, Any]:
    """
    Weather + Track Evolution Index (TEI) v1.1 (cleaner)

    Improvements vs v1:
    - Apply a global "quick lap" threshold before bucketing to avoid slow-lap contamination.
    """
    TEI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = TEI_CACHE_DIR / f"weather_tei_{season}_{round}_{session_name}.json"

    # Return cached result if exists
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    session = fastf1.get_session(season, round, session_name)
    session.load(weather=True, laps=True)

    # -----------------------
    # Weather
    # -----------------------
    weather_records: List[Dict[str, Any]] = []
    w = session.weather_data
    if w is not None and not w.empty:
        wdf = w.copy()
        wdf["Time"] = wdf["Time"].astype(str)
        cols = ["Time", "AirTemp", "TrackTemp", "Rainfall", "WindSpeed", "WindDirection"]
        weather_records = wdf[cols].to_dict(orient="records")

    # -----------------------
    # TEI
    # -----------------------
    laps = session.laps
    if laps is None or laps.empty:
        out = {
            "season": season,
            "round": round,
            "session": session_name,
            "weather": weather_records,
            "tei": [],
            "message": "No lap data available to compute TEI"
        }
        cache_path.write_text(json.dumps(out))
        return out

    df = laps[["Time", "LapTime", "PitInTime", "PitOutTime", "IsAccurate"]].copy()
    df = df[df["LapTime"].notna()]
    df = df[df["IsAccurate"] == True]
    df = df[df["PitInTime"].isna() & df["PitOutTime"].isna()]

    if df.empty:
        out = {
            "season": season,
            "round": round,
            "session": session_name,
            "weather": weather_records,
            "tei": [],
            "message": "No clean laps available to compute TEI"
        }
        cache_path.write_text(json.dumps(out))
        return out

    df["lap_s"] = df["LapTime"].dt.total_seconds()
    df["t_s"] = df["Time"].dt.total_seconds()

    # Global quick-lap filter (removes very slow laps)
    # Keep fastest 60% laps globally
    global_q = float(df["lap_s"].quantile(0.60))
    df = df[df["lap_s"] <= global_q]

    if df.empty:
        out = {
            "season": season,
            "round": round,
            "session": session_name,
            "weather": weather_records,
            "tei": [],
            "message": "After quick-lap filtering, no laps remain for TEI"
        }
        cache_path.write_text(json.dumps(out))
        return out

    bucket_s = 60.0
    df["bucket"] = (df["t_s"] // bucket_s).astype(int)

    global_best = float(df["lap_s"].min())

    tei_rows: List[Dict[str, Any]] = []
    for b, g in df.groupby("bucket"):
        # representative time in this bucket = median lap time
        median_lap = float(g["lap_s"].median())
        tei = float(global_best / median_lap)

        tei_rows.append({
            "t_s": float(b * bucket_s),
            "median_lap_s": median_lap,
            "tei": tei
        })

    tei_rows.sort(key=lambda x: x["t_s"])

    out = {
        "season": season,
        "round": round,
        "session": session_name,
        "weather": weather_records,
        "tei": tei_rows,
        "message": "Weather + TEI computed (v1.1)"
    }

    cache_path.write_text(json.dumps(out))
    return out
