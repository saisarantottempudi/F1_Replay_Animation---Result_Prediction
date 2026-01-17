from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import fastf1

fastf1.Cache.enable_cache("cache")


def _to_seconds(td) -> float:
    if pd.isna(td):
        return float("nan")
    return pd.to_timedelta(td).total_seconds()


def _quick_laps(df: pd.DataFrame, q: float = 0.75) -> pd.DataFrame:
    """
    Keep quicker laps (remove slow tail). Uses lap_s quantile per group.
    """
    if df.empty:
        return df
    thresh = float(df["lap_s"].quantile(q))
    return df[df["lap_s"] <= thresh].copy()


def _stint_pace(laps: pd.DataFrame, q: float = 0.75) -> Optional[float]:
    """
    Robust pace estimate for a stint: median of quick laps.
    """
    if laps.empty:
        return None
    laps2 = _quick_laps(laps, q=q)
    if laps2.empty:
        return None
    return float(laps2["lap_s"].median())


def _pit_laps(laps: pd.DataFrame) -> List[int]:
    """
    Extract pit-in laps (where PitInTime exists).
    """
    if laps.empty or "PitInTime" not in laps.columns:
        return []
    pl = laps[~laps["PitInTime"].isna()]["LapNumber"].dropna().astype(int).tolist()
    # de-duplicate and sort
    return sorted(list(dict.fromkeys(pl)))


def compute_strategy_intelligence(
    season: int,
    round_no: int,
    degradation_threshold_sec_per_lap: float = 0.06,
    quick_quantile: float = 0.75,
) -> Dict[str, Any]:
    """
    Strategy Intelligence v1:
    - per driver: pit stop laps, stint pace, stint degradation slope
    - global: suggested pit window when degradation exceeds threshold (driver-specific)
    - undercut/overcut heuristic: compare pre/post pit pace around pit events
    """
    session = fastf1.get_session(season, round_no, "R")
    session.load(weather=False, telemetry=False, messages=False)

    laps_all = session.laps.copy()
    if laps_all.empty:
        return {"season": season, "round": round_no, "message": "No laps available", "drivers": []}

    # Precompute lap seconds
    laps_all["lap_s"] = laps_all["LapTime"].apply(_to_seconds)
    laps_all = laps_all.dropna(subset=["LapNumber", "lap_s", "Driver"])

    # Identify pit marker
    laps_all["is_pit"] = (~laps_all.get("PitInTime").isna()) | (~laps_all.get("PitOutTime").isna())

    drivers = sorted(laps_all["Driver"].unique().tolist())

    drivers_out: List[Dict[str, Any]] = []

    # Build stint blocks using FastF1 Stint + Compound (if missing, still works)
    for d in drivers:
        dlaps = laps_all[laps_all["Driver"] == d].copy()
        if dlaps.empty:
            continue

        pit_laps = _pit_laps(dlaps)

        stints: List[Dict[str, Any]] = []
        if "Stint" in dlaps.columns and "Compound" in dlaps.columns:
            grouped = dlaps.groupby(["Stint", "Compound"], dropna=False)
        else:
            # fallback: single stint
            grouped = [(("NA", dlaps.get("Compound", pd.Series(["UNKNOWN"])).iloc[0] if "Compound" in dlaps.columns else "UNKNOWN"), dlaps)]

        for (stint_no, compound), g in grouped:
            g = g.sort_values("LapNumber").copy()
            lap_start = int(g["LapNumber"].min())
            lap_end = int(g["LapNumber"].max())

            # Remove pit laps for analysis
            g2 = g[~g["is_pit"]].copy()
            pace = _stint_pace(g2, q=quick_quantile)

            # Degradation slope (sec/lap) quick-laps linear fit
            slope = None
            r2 = None
            if g2.shape[0] >= 5:
                gq = _quick_laps(g2, q=quick_quantile)
                if gq.shape[0] >= 5:
                    x = gq["LapNumber"].to_numpy(dtype=float)
                    y = gq["lap_s"].to_numpy(dtype=float)
                    a, b = np.polyfit(x, y, 1)
                    yhat = a * x + b
                    ss_res = float(np.sum((y - yhat) ** 2))
                    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
                    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
                    slope = float(a)

            # Suggested pit window for this stint if degradation is high
            pit_window = None
            if slope is not None and slope >= degradation_threshold_sec_per_lap:
                # simple: suggest middle-to-late part of stint
                pit_window = {
                    "from_lap": max(lap_start, int(lap_start + (lap_end - lap_start) * 0.55)),
                    "to_lap": max(lap_start, int(lap_start + (lap_end - lap_start) * 0.85)),
                    "reason": f"Degradation slope {slope:.3f} sec/lap exceeds threshold {degradation_threshold_sec_per_lap:.3f}",
                }

            stints.append(
                {
                    "stint": None if pd.isna(stint_no) else int(stint_no) if str(stint_no).isdigit() else str(stint_no),
                    "compound": str(compound),
                    "lap_start": lap_start,
                    "lap_end": lap_end,
                    "pace_median_quick_s": pace,
                    "deg_slope_sec_per_lap": slope,
                    "deg_r2": r2,
                    "suggested_pit_window": pit_window,
                }
            )

        stints.sort(key=lambda s: s["lap_start"])

        # Undercut/Overcut heuristic around each pit lap:
        # Compare median lap_s in 3 laps before pit vs 3 laps after pit (excluding pit laps)
        battles = []
        for plap in pit_laps:
            pre = dlaps[(dlaps["LapNumber"] >= plap - 3) & (dlaps["LapNumber"] <= plap - 1) & (~dlaps["is_pit"])]
            post = dlaps[(dlaps["LapNumber"] >= plap + 1) & (dlaps["LapNumber"] <= plap + 3) & (~dlaps["is_pit"])]

            pre_pace = _stint_pace(pre, q=1.0)  # already short window; no quantile filter
            post_pace = _stint_pace(post, q=1.0)

            delta = None
            if pre_pace is not None and post_pace is not None:
                delta = float(pre_pace - post_pace)  # positive means faster after pit

            battles.append(
                {
                    "pit_lap": int(plap),
                    "pre_window_pace_s": pre_pace,
                    "post_window_pace_s": post_pace,
                    "pace_gain_s": delta,
                    "label": "undercut_like" if (delta is not None and delta > 0.15) else "neutral",
                    "note": "Positive pace_gain_s suggests fresher tyre benefit (undercut-like).",
                }
            )

        drivers_out.append(
            {
                "driver": d,
                "pit_laps": pit_laps,
                "stints": stints,
                "pit_effects": battles,
            }
        )

    return {
        "season": season,
        "round": round_no,
        "session": "R",
        "params": {
            "degradation_threshold_sec_per_lap": degradation_threshold_sec_per_lap,
            "quick_quantile": quick_quantile,
            "pit_effect_window_laps": 3,
        },
        "drivers": drivers_out,
        "message": "Strategy intelligence computed (v1)",
    }
