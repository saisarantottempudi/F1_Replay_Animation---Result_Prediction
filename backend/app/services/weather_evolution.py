from __future__ import annotations

from typing import Dict, Any, List
import fastf1
import pandas as pd


def load_weather_and_tei(season: int, round: int, session_name: str) -> Dict[str, Any]:
    """
    Weather + Track Evolution Index (TEI) v1

    TEI concept (v1):
    - As the session progresses, grip increases, so representative lap times reduce.
    - We bucket session time into windows and compute median of the "quick laps" in each bucket.
    - TEI is normalized as: TEI = best_lap / bucket_median_quick_lap
      so TEI increases as lap times improve.
    """
    session = fastf1.get_session(season, round, session_name)
    session.load(weather=True, laps=True)

    # -----------------------
    # Weather data
    # -----------------------
    weather_records: List[Dict[str, Any]] = []
    w = session.weather_data
    if w is not None and not w.empty:
        wdf = w.copy()
        wdf["Time"] = wdf["Time"].astype(str)
        cols = ["Time", "AirTemp", "TrackTemp", "Rainfall", "WindSpeed", "WindDirection"]
        weather_records = wdf[cols].to_dict(orient="records")

    # -----------------------
    # Lap data for TEI
    # -----------------------
    laps = session.laps
    if laps is None or laps.empty:
        return {
            "season": season,
            "round": round,
            "session": session_name,
            "weather": weather_records,
            "tei": [],
            "message": "No lap data available to compute TEI"
        }

    df = laps[["Time", "LapTime", "PitInTime", "PitOutTime", "IsAccurate"]].copy()
    df = df[df["LapTime"].notna()]
    df = df[df["IsAccurate"] == True]
    df = df[df["PitInTime"].isna() & df["PitOutTime"].isna()]

    if df.empty:
        return {
            "season": season,
            "round": round,
            "session": session_name,
            "weather": weather_records,
            "tei": [],
            "message": "No clean laps available to compute TEI"
        }

    # Convert time to seconds
    df["lap_s"] = df["LapTime"].dt.total_seconds()
    df["t_s"] = df["Time"].dt.total_seconds()

    # TEI computation
    bucket_s = 60.0
    df["bucket"] = (df["t_s"] // bucket_s).astype(int)

    global_best = float(df["lap_s"].min())

    tei_rows: List[Dict[str, Any]] = []
    for b, g in df.groupby("bucket"):
        # "quick laps" = fastest 25% within bucket
        q25 = g["lap_s"].quantile(0.25)
        quick = g[g["lap_s"] <= q25]
        if quick.empty:
            continue

        median_quick = float(quick["lap_s"].median())
        tei = float(global_best / median_quick)

        tei_rows.append({
            "t_s": float(b * bucket_s),
            "median_quick_lap_s": median_quick,
            "tei": tei
        })

    tei_rows.sort(key=lambda x: x["t_s"])

    return {
        "season": season,
        "round": round,
        "session": session_name,
        "weather": weather_records,
        "tei": tei_rows,
        "message": "Weather + TEI computed (v1)"
    }
