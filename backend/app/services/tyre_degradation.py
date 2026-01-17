from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import fastf1


# IMPORTANT: use project cache directory
fastf1.Cache.enable_cache("cache")


@dataclass
class StintDegradation:
    compound: str
    lap_start: int
    lap_end: int
    laps_used: int
    best_lap_s: float
    slope_sec_per_lap: float
    intercept_s: float
    r2: float
    message: str


def _to_seconds(td) -> float:
    # fastf1 uses pandas Timedelta; sometimes returns NaT
    if pd.isna(td):
        return float("nan")
    return pd.to_timedelta(td).total_seconds()


def _linear_fit(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """
    Fit y = a*x + b
    Returns (a, b, r2)
    """
    if len(x) < 2:
        return 0.0, float(y.mean()) if len(y) else 0.0, 0.0
    a, b = np.polyfit(x, y, 1)
    y_hat = a * x + b
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(a), float(b), float(r2)


def compute_tyre_degradation(
    season: int,
    round_no: int,
    session_code: str,
    driver: str,
    min_laps: int = 5,
    quick_quantile: float = 0.75,
) -> Dict[str, Any]:
    """
    For a given driver + session:
    - segment by stints (compound blocks)
    - filter out in/out laps + slow laps using quantile threshold per stint
    - compute degradation slope (sec/lap) using linear regression
    """
    session = fastf1.get_session(season, round_no, session_code)
    session.load(weather=False, telemetry=False, messages=False)

    laps = session.laps.pick_driver(driver).copy()
    if laps.empty:
        return {
            "season": season,
            "round": round_no,
            "session": session_code,
            "driver": driver,
            "stints": [],
            "message": "No laps found for driver in this session",
        }

    # Ensure needed columns exist
    needed = ["LapNumber", "LapTime", "Compound", "Stint", "PitInTime", "PitOutTime"]
    for c in needed:
        if c not in laps.columns:
            # Don't hard fail; FastF1 can vary
            laps[c] = np.nan

    # Compute lap time in seconds
    laps["lap_s"] = laps["LapTime"].apply(_to_seconds)

    # Drop obviously invalid laps
    laps = laps.dropna(subset=["LapNumber", "lap_s", "Compound"])
    if laps.empty:
        return {
            "season": season,
            "round": round_no,
            "session": session_code,
            "driver": driver,
            "stints": [],
            "message": "No valid timed laps for driver in this session",
        }

    # Identify "in/out" style laps: if PitInTime or PitOutTime exists on that lap, drop from analysis
    # (We still keep the stint boundaries using LapNumber range)
    laps["is_pit"] = (~laps["PitInTime"].isna()) | (~laps["PitOutTime"].isna())

    stints_out: List[Dict[str, Any]] = []

    # Group by Stint + Compound (stint is stable in race; in quali it still helps)
    grouped = laps.groupby(["Stint", "Compound"], dropna=False)

    for (stint_no, compound), g in grouped:
        g = g.sort_values("LapNumber").copy()
        lap_start = int(g["LapNumber"].min())
        lap_end = int(g["LapNumber"].max())

        # analysis subset: remove pit laps
        g2 = g[~g["is_pit"]].copy()
        if g2.empty:
            stints_out.append(
                {
                    "compound": str(compound),
                    "lap_start": lap_start,
                    "lap_end": lap_end,
                    "laps_used": 0,
                    "best_lap_s": None,
                    "slope_sec_per_lap": None,
                    "r2": None,
                    "message": "No non-pit laps available for this stint",
                }
            )
            continue

        # quick laps filter (remove the slow tail)
        thresh = float(g2["lap_s"].quantile(quick_quantile))
        g2 = g2[g2["lap_s"] <= thresh].copy()

        if len(g2) < min_laps:
            stints_out.append(
                {
                    "compound": str(compound),
                    "lap_start": lap_start,
                    "lap_end": lap_end,
                    "laps_used": int(len(g2)),
                    "best_lap_s": float(g["lap_s"].min()),
                    "slope_sec_per_lap": None,
                    "r2": None,
                    "message": f"Not enough quick laps for fit (need {min_laps}, got {len(g2)})",
                }
            )
            continue

        x = g2["LapNumber"].to_numpy(dtype=float)
        y = g2["lap_s"].to_numpy(dtype=float)

        a, b, r2 = _linear_fit(x, y)
        best_lap = float(g["lap_s"].min())

        stints_out.append(
            {
                "compound": str(compound),
                "lap_start": lap_start,
                "lap_end": lap_end,
                "laps_used": int(len(g2)),
                "best_lap_s": best_lap,
                "slope_sec_per_lap": float(a),
                "intercept_s": float(b),
                "r2": float(r2),
                "message": "OK",
            }
        )

    # Sort stints by lap_start
    stints_out.sort(key=lambda s: (s["lap_start"], s["compound"]))

    return {
        "season": season,
        "round": round_no,
        "session": session_code,
        "driver": driver,
        "stints": stints_out,
        "meta": {
            "min_laps": min_laps,
            "quick_quantile": quick_quantile,
            "note": "Slope is sec/lap (positive = degrading). Uses quick-laps quantile filter per stint.",
        },
        "message": "Tyre degradation computed (v1)",
    }
