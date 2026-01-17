from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import fastf1

fastf1.Cache.enable_cache("cache")


def build_features_for_event(season: int, round_no: int) -> pd.DataFrame:
    """
    Build one row per driver with only pre-race features:
    - driver, team
    - grid_pos (from Race session starting grid)
    - quali_best_s (from Qualifying best lap)
    - season
    - round
    NOTE: v1 uses minimal set so it matches your trained model expectations.
    """
    # Qualifying
    q = fastf1.get_session(season, round_no, "Q")
    q.load()

    # Race (for grid positions)
    r = fastf1.get_session(season, round_no, "R")
    r.load()

    # Build quali best lap per driver
    qlaps = q.laps
    qbest = (
        qlaps.groupby("Driver")["LapTime"]
        .min()
        .dropna()
        .dt.total_seconds()
        .rename("quali_best_s")
        .reset_index()
    )

    # Grid from race results / starting grid
    # FastF1: r.results has GridPosition sometimes; fallback to Position in first lap order is risky
    if r.results is None or len(r.results) == 0:
        raise ValueError("Race results/grid not available for this event (FastF1 returned empty results).")

    res = r.results.copy()
    # Standardize cols
    cols = res.columns
    driver_col = "Abbreviation" if "Abbreviation" in cols else "DriverNumber"
    team_col = "TeamName" if "TeamName" in cols else "Team"
    grid_col = "GridPosition" if "GridPosition" in cols else "Grid"

    if grid_col not in cols:
        raise ValueError(f"Grid column not found in results. Available: {list(cols)}")

    base = pd.DataFrame({
        "driver": res[driver_col].astype(str),
        "team": res[team_col].astype(str) if team_col in cols else "UNKNOWN",
        "grid_pos": pd.to_numeric(res[grid_col], errors="coerce"),
    })

    # Merge quali
    base = base.merge(qbest, left_on="driver", right_on="Driver", how="left").drop(columns=["Driver"])
    base["season"] = int(season)
    base["round"] = int(round_no)

    # Minimal placeholders for rolling/team form (v1)
    # Later we will compute these from historical parquet.
    for c in [
        "drv_roll_points","drv_roll_finish","drv_roll_grid","drv_roll_quali","drv_roll_pos_delta",
        "team_roll_points","team_roll_finish",
        "incident","sc","vsc","red_flag"
    ]:
        base[c] = 0.0

    return base
