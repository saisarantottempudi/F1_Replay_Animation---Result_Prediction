from __future__ import annotations

import pandas as pd
import numpy as np


def _safe_points(pos: float) -> float:
    """
    Approx FIA points (top 10). Not perfect but good baseline.
    """
    if pd.isna(pos):
        return 0.0
    pos = int(pos)
    pts = {1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}
    return float(pts.get(pos, 0))


def add_features(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    df = df.copy()

    # Data cleaning: ensure season/round/driver exist
    df['season'] = pd.to_numeric(df.get('season'), errors='coerce')
    df['round'] = pd.to_numeric(df.get('round'), errors='coerce')
    df = df.dropna(subset=['season','round','driver'])
    df['season'] = df['season'].astype(int)
    df['round'] = df['round'].astype(int)

    # sort timeline
    df["race_index"] = df["season"].astype(int) * 100 + df["round"].astype(int)
    df = df.sort_values(["driver", "race_index"])

    # base points
    df["points"] = df["finish_pos"].apply(_safe_points)

    # driver rolling form
    df["drv_roll_points"] = (
        df.groupby("driver")["points"]
          .apply(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
          .reset_index(level=0, drop=True)
    )
    df["drv_roll_finish"] = (
        df.groupby("driver")["finish_pos"]
          .apply(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
          .reset_index(level=0, drop=True)
    )
    df["drv_roll_grid"] = (
        df.groupby("driver")["grid_pos"]
          .apply(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
          .reset_index(level=0, drop=True)
    )
    df["drv_roll_quali"] = (
        df.groupby("driver")["quali_best_s"]
          .apply(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
          .reset_index(level=0, drop=True)
    )

    # racecraft = finish - grid (negative = gained positions)
    df["pos_delta"] = df["finish_pos"] - df["grid_pos"]
    df["drv_roll_pos_delta"] = (
        df.groupby("driver")["pos_delta"]
          .apply(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
          .reset_index(level=0, drop=True)
    )

    # team rolling form
    df = df.sort_values(["team", "race_index"])
    df["team_roll_points"] = (
        df.groupby("team")["points"]
          .apply(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
          .reset_index(level=0, drop=True)
    )
    df["team_roll_finish"] = (
        df.groupby("team")["finish_pos"]
          .apply(lambda s: s.shift(1).rolling(window, min_periods=1).mean())
          .reset_index(level=0, drop=True)
    )

    # reset ordering
    df = df.sort_values(["season", "round", "driver"])
    return df


def main():
    in_path = "data/ml/driver_event_table_v1_2_strategy.parquet"
    df = pd.read_parquet(in_path)

    out = add_features(df, window=5)

    out_path = "data/ml/driver_event_table_v1_3_features.parquet"
    out.to_parquet(out_path, index=False)

    print(f"✅ Saved: {out_path}")
    cols = ["season","round","driver","team","grid_pos","finish_pos","drv_roll_points","team_roll_points","drv_roll_quali","drv_roll_pos_delta"]
    print(out[cols].dropna().head(20).to_string(index=False))


if __name__ == "__main__":
    main()
