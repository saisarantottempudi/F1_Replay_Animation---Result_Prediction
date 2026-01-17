from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import fastf1

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


def _to_seconds(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(pd.to_timedelta(x).total_seconds())
    except Exception:
        return None


def _robust_quick_pace(laptimes_s: np.ndarray, quick_q: float = 0.75, outlier_s: float = 7.0) -> Optional[float]:
    if laptimes_s is None or len(laptimes_s) == 0:
        return None
    med = float(np.median(laptimes_s))
    laptimes_s = laptimes_s[laptimes_s <= med + outlier_s]
    if len(laptimes_s) < 3:
        return None
    q = float(np.quantile(laptimes_s, quick_q))
    quick = laptimes_s[laptimes_s <= q]
    if len(quick) < 3:
        return None
    return float(np.median(quick))


def _linear_deg_slope(lap_idx: np.ndarray, laptimes_s: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
    """
    Returns (slope_sec_per_lap, r2)
    """
    if len(lap_idx) < 5:
        return None, None
    x = lap_idx.astype(float)
    y = laptimes_s.astype(float)
    # simple linear fit
    a, b = np.polyfit(x, y, 1)
    yhat = a * x + b
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2)) or 1.0
    r2 = 1.0 - ss_res / ss_tot
    return float(a), float(r2)


def extract_driver_strategy_features(season: int, round_no: int) -> pd.DataFrame:
    """
    Builds per-driver strategy signals from the Race session:
    - pit stops from stints
    - per-stint pace and degradation slope
    - undercut proxy: pace gain after pit (windowed)
    """
    event = fastf1.get_event(season, round_no)
    r = event.get_race()
    r.load(messages=False, weather=False)

    laps = r.laps
    if laps is None or len(laps) == 0:
        return pd.DataFrame([])

    # FastF1 has Stint, Compound columns in laps for races usually
    # We'll derive stints per driver: contiguous stint id
    drivers = sorted(list(set(laps["Driver"].dropna().unique().tolist())))
    rows: List[Dict[str, Any]] = []

    for drv in drivers:
        dl = laps.pick_drivers([drv])  # avoids deprecated pick_driver
        dl = dl.dropna(subset=["LapNumber", "LapTime"])
        if len(dl) < 8:
            continue

        # detect pit laps via Stint changes
        if "Stint" in dl.columns:
            stints = dl[["LapNumber", "Stint", "Compound"]].dropna(subset=["Stint"])
            stint_ids = stints["Stint"].astype(int)
            pit_laps = stints.loc[stint_ids.diff().fillna(0) != 0, "LapNumber"].astype(int).tolist()
        else:
            pit_laps = []

        num_stops = max(0, len(pit_laps))

        # Strategy labels
        label_one_stop = 1 if num_stops == 1 else 0
        label_two_plus = 1 if num_stops >= 2 else 0

        # undercut proxy: compare quick pace in 3 laps before vs 3 laps after each pit
        lapt_s = dl["LapTime"].apply(_to_seconds).dropna().astype(float).values
        lapn = dl["LapNumber"].dropna().astype(int).values

        undercut_gains = []
        for pl in pit_laps:
            pre_mask = (lapn >= pl - 3) & (lapn <= pl - 1)
            post_mask = (lapn >= pl + 1) & (lapn <= pl + 3)
            pre = lapt_s[pre_mask] if pre_mask.any() else np.array([])
            post = lapt_s[post_mask] if post_mask.any() else np.array([])
            pre_p = _robust_quick_pace(pre) if len(pre) else None
            post_p = _robust_quick_pace(post) if len(post) else None
            if pre_p is not None and post_p is not None:
                undercut_gains.append(pre_p - post_p)  # positive = gained pace

        undercut_gain = float(np.max(undercut_gains)) if undercut_gains else 0.0

        # degradation proxy: compute per-stint slope using Stint column if available
        deg_slopes = []
        deg_r2s = []
        if "Stint" in dl.columns:
            for stint_id, grp in dl.groupby("Stint"):
                g = grp.dropna(subset=["LapNumber", "LapTime"])
                if len(g) < 6:
                    continue
                lt = g["LapTime"].apply(_to_seconds).dropna().astype(float).values
                ln = g["LapNumber"].dropna().astype(int).values
                # focus on quick laps only
                qp = _robust_quick_pace(lt)
                if qp is None:
                    continue
                q = float(np.quantile(lt, 0.75))
                ltq = lt[lt <= q]
                lnq = ln[: len(ltq)]
                if len(ltq) < 5:
                    continue
                slope, r2 = _linear_deg_slope(lnq, ltq)
                if slope is not None:
                    deg_slopes.append(slope)
                    deg_r2s.append(r2 if r2 is not None else 0.0)

        max_deg_slope = float(np.max(deg_slopes)) if deg_slopes else 0.0
        avg_deg_r2 = float(np.mean(deg_r2s)) if deg_r2s else 0.0

        # heuristic label: high degradation
        label_high_deg = 1 if max_deg_slope >= 0.06 else 0

        rows.append({
            "season": season,
            "round": round_no,
            "driver": drv,
            "stops": num_stops,
            "label_one_stop": label_one_stop,
            "label_two_plus": label_two_plus,
            "undercut_gain_s": undercut_gain,
            "max_deg_slope_sec_per_lap": max_deg_slope,
            "avg_deg_r2": avg_deg_r2,
            "label_high_deg": label_high_deg,
        })

    return pd.DataFrame(rows)


def main():
    in_path = "data/ml/driver_event_table_v1_1_incidents.parquet"
    df = pd.read_parquet(in_path)

    seasons = sorted([int(x) for x in df["season"].dropna().unique().tolist()])
    rounds = df[["season", "round"]].dropna().drop_duplicates().sort_values(["season", "round"])

    all_rows = []
    for _, row in rounds.iterrows():
        season = int(row["season"])
        round_no = int(row["round"])
        try:
            s = extract_driver_strategy_features(season, round_no)
            if len(s) > 0:
                all_rows.append(s)
        except Exception as e:
            # skip race if API issues
            continue

    strat = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame([])

    out = df.merge(
        strat,
        how="left",
        left_on=["season", "round", "driver"],
        right_on=["season", "round", "driver"],
    )

    out_path = "data/ml/driver_event_table_v1_2_strategy.parquet"
    out.to_parquet(out_path, index=False)

    print(f"✅ Saved: {out_path}")
    cols = ["season","round","driver","stops","label_one_stop","label_two_plus","undercut_gain_s","max_deg_slope_sec_per_lap","label_high_deg"]
    print(out[cols].dropna().head(20).to_string(index=False))


if __name__ == "__main__":
    main()
