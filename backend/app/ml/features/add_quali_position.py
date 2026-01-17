from __future__ import annotations

from pathlib import Path
import pandas as pd

IN_PATH = Path("data/ml/driver_event_table_v1_3_features.parquet")
OUT_PATH = Path("data/ml/driver_event_table_v1_4_quali_pos.parquet")


def main():
    df = pd.read_parquet(IN_PATH)

    # If quali_pos already exists, just re-save
    if "quali_pos" in df.columns:
        df.to_parquet(OUT_PATH, index=False)
        print(f"✅ Saved (already had quali_pos): {OUT_PATH}")
        return

    # Build quali position from quali_best_s (lower is faster)
    if "quali_best_s" not in df.columns:
        raise ValueError("quali_best_s not found. Cannot compute quali_pos.")

    df = df.copy()
    df["quali_best_s"] = pd.to_numeric(df["quali_best_s"], errors="coerce")

    # Rank within each event (season, round)
    df["quali_pos"] = (
        df.groupby(["season", "round"])["quali_best_s"]
          .rank(method="min", ascending=True)
    )

    # Some drivers might not have quali time; keep as NaN
    df.to_parquet(OUT_PATH, index=False)
    print(f"✅ Saved: {OUT_PATH}")
    print("Columns:", list(df.columns))


if __name__ == "__main__":
    main()
