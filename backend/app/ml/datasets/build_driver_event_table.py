from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd
import fastf1

# Cache safety
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


@dataclass
class BuildParams:
    seasons: List[int]
    quick_quantile: float = 0.75
    outlier_seconds: float = 7.0
    min_race_laps: int = 6


def _to_seconds(x) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(pd.to_timedelta(x).total_seconds())
    except Exception:
        return None


def _robust_race_pace_seconds(r_laps: pd.DataFrame, quick_quantile: float, outlier_seconds: float, min_laps: int) -> Tuple[Optional[float], int]:
    if r_laps is None or len(r_laps) == 0:
        return None, 0

    lt = r_laps["LapTime"].dropna()
    if len(lt) < min_laps:
        return None, int(len(lt))

    lap_s = lt.apply(_to_seconds).dropna().astype(float)
    if len(lap_s) < min_laps:
        return None, int(len(lap_s))

    med = float(np.median(lap_s))
    lap_s = lap_s[lap_s <= med + outlier_seconds]
    if len(lap_s) < min_laps:
        return None, int(len(lap_s))

    q = float(np.quantile(lap_s, quick_quantile))
    quick = lap_s[lap_s <= q]
    if len(quick) < min_laps:
        return None, int(len(quick))

    return float(np.median(quick)), int(len(quick))


def build_table(params: BuildParams) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for season in params.seasons:
        try:
            schedule = fastf1.get_event_schedule(season)
        except Exception as e:
            rows.append({
                "season": season,
                "round": None,
                "event": None,
                "driver": None,
                "error": f"schedule_failed: {e}",
            })
            continue
        # Use only official rounds (skip testing / round 0)
        schedule = schedule[schedule["RoundNumber"].fillna(0).astype(int) > 0]

        for _, ev in schedule.iterrows():
            round_no = int(ev["RoundNumber"])
            event_name = str(ev["EventName"])

            try:
                event = fastf1.get_event(season, round_no)
                q = event.get_qualifying()
                r = event.get_race()

                q.load(messages=False, weather=False)
                r.load(messages=False, weather=False)

                # Guard: sometimes FastF1 fails to load a session (0 drivers / no laps)
                # In that case, skip this event instead of crashing the whole build.
                if not getattr(q, '_laps', None) is not None and getattr(q, 'laps', None) is None:
                    raise RuntimeError('qualifying_laps_not_loaded')
                if not getattr(r, '_laps', None) is not None and getattr(r, 'laps', None) is None:
                    raise RuntimeError('race_laps_not_loaded')

            except Exception as e:
                rows.append({
                    "season": season,
                    "round": round_no,
                    "event": event_name,
                    "driver": None,
                    "error": f"load_failed: {e}",
                })
                continue

            # --- Qualifying features ---
            try:
                qlaps = q.laps
                rlaps = r.laps
            except Exception as e:
                rows.append({
                    'season': season,
                    'round': round_no,
                    'event': event_name,
                    'driver': None,
                    'error': f'data_not_loaded: {e}',
                })
                continue

            # best lap time per driver
            q_best = (
                qlaps.dropna(subset=["Driver", "LapTime"])
                .groupby("Driver")["LapTime"]
                .min()
                .apply(_to_seconds)
                .dropna()
            )
            # Grid position for race (from race result / laps data)
            # FastF1: race.session_results has GridPosition and Position
            try:
                res = r.results  # DataFrame
            except Exception:
                res = None

            # --- Race labels + race training-only features ---

            drivers = sorted(list(set(rlaps["Driver"].dropna().unique().tolist())))

            # finishing positions
            pos_map: Dict[str, int] = {}
            constructor_map: Dict[str, str] = {}
            grid_map: Dict[str, Optional[int]] = {}

            if res is not None and len(res) > 0:
                for _, rr in res.iterrows():
                    drv = rr.get("Abbreviation")
                    if not drv:
                        continue
                    try:
                        pos_map[str(drv)] = int(rr.get("Position"))
                    except Exception:
                        pass
                    constructor_map[str(drv)] = str(rr.get("TeamName") or "")
                    try:
                        grid_map[str(drv)] = int(rr.get("GridPosition"))
                    except Exception:
                        grid_map[str(drv)] = None

            for drv in drivers:
                rdrv = rlaps.pick_driver(drv)
                race_pace_s, laps_used = _robust_race_pace_seconds(
                    rdrv,
                    params.quick_quantile,
                    params.outlier_seconds,
                    params.min_race_laps,
                )

                finish_pos = pos_map.get(drv)
                grid_pos = grid_map.get(drv)

                rows.append({
                    "season": season,
                    "round": round_no,
                    "event": event_name,
                    "driver": drv,
                    "team": constructor_map.get(drv, ""),
                    # features
                    "grid_pos": grid_pos,
                    "quali_best_s": float(q_best.get(drv)) if drv in q_best.index else None,
                    # training-only (do NOT use for pre-race inference)
                    "race_pace_s": race_pace_s,
                    "race_laps_used": laps_used,
                    # labels
                    "finish_pos": finish_pos,
                    "label_win": 1 if finish_pos == 1 else 0 if finish_pos else None,
                    "label_top3": 1 if finish_pos and finish_pos <= 3 else 0 if finish_pos else None,
                    # pole labels from grid
                    "label_pole": 1 if grid_pos == 1 else 0 if grid_pos else None,
                    "label_quali_top3": 1 if grid_pos and grid_pos <= 3 else 0 if grid_pos else None,
                    "error": None,
                })

    df = pd.DataFrame(rows)
    return df


def main():
    params = BuildParams(seasons=[2019, 2020, 2021, 2022, 2023, 2024])
    df = build_table(params)

    out = "data/ml/driver_event_table_v1.parquet"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    df.to_parquet(out, index=False)

    print(f"✅ Saved: {out}")
    print(df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
