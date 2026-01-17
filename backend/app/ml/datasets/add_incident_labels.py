from __future__ import annotations

import os
from typing import Dict, Any, List

import pandas as pd
import fastf1

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)


def _has_incident_from_messages(messages_df: pd.DataFrame) -> Dict[str, int]:
    """
    Detect SC/VSC/Red Flag using RaceControlMessages.
    Returns dict with keys: sc, vsc, red, incident
    """
    if messages_df is None or len(messages_df) == 0:
        return {"sc": 0, "vsc": 0, "red": 0, "incident": 0}

    # FastF1 RCM columns vary; we safely search text
    text_cols = [c for c in messages_df.columns if c.lower() in ("message", "category", "flag", "status")]
    if not text_cols:
        # fallback: stringify whole rows
        combined = messages_df.astype(str).agg(" ".join, axis=1).str.upper()
    else:
        combined = messages_df[text_cols].astype(str).agg(" ".join, axis=1).str.upper()

    has_sc = int(combined.str.contains("SAFETY CAR").any() or combined.str.contains(r"\bSC\b").any())
    has_vsc = int(combined.str.contains("VSC").any() or combined.str.contains("VIRTUAL SAFETY").any())
    has_red = int(combined.str.contains("RED FLAG").any())

    incident = int((has_sc or has_vsc or has_red) == 1)
    return {"sc": has_sc, "vsc": has_vsc, "red": has_red, "incident": incident}


def build_incident_table(seasons: List[int]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []

    for season in seasons:
        try:
            schedule = fastf1.get_event_schedule(season)
            schedule = schedule[schedule["RoundNumber"].fillna(0).astype(int) > 0]
        except Exception as e:
            rows.append({"season": season, "round": None, "error": f"schedule_failed: {e}"})
            continue

        for _, ev in schedule.iterrows():
            round_no = int(ev["RoundNumber"])
            event_name = str(ev["EventName"])

            try:
                event = fastf1.get_event(season, round_no)
                r = event.get_race()
                r.load(messages=True, weather=False)
            except Exception as e:
                rows.append({
                    "season": season,
                    "round": round_no,
                    "event": event_name,
                    "sc": 0,
                    "vsc": 0,
                    "red_flag": 0,
                    "incident": 0,
                    "error": f"race_load_failed: {e}",
                })
                continue

            try:
                messages = getattr(r, "race_control_messages", None)
                if messages is None:
                    # fallback attempt
                    messages = getattr(r, "race_control_messages_data", None)
                info = _has_incident_from_messages(messages)
                rows.append({
                    "season": season,
                    "round": round_no,
                    "event": event_name,
                    "sc": info["sc"],
                    "vsc": info["vsc"],
                    "red_flag": info["red"],
                    "incident": info["incident"],
                    "error": None,
                })
            except Exception as e:
                rows.append({
                    "season": season,
                    "round": round_no,
                    "event": event_name,
                    "sc": 0,
                    "vsc": 0,
                    "red_flag": 0,
                    "incident": 0,
                    "error": f"message_parse_failed: {e}",
                })

    return pd.DataFrame(rows)


def main():
    in_path = "data/ml/driver_event_table_v1.parquet"
    df = pd.read_parquet(in_path)

    seasons = sorted([int(x) for x in df["season"].dropna().unique().tolist()])
    inc = build_incident_table(seasons)

    # merge labels back to driver-event table (broadcast to all drivers in same race)
    out = df.merge(
        inc[["season", "round", "sc", "vsc", "red_flag", "incident"]],
        how="left",
        left_on=["season", "round"],
        right_on=["season", "round"],
    )

    out_path = "data/ml/driver_event_table_v1_1_incidents.parquet"
    out.to_parquet(out_path, index=False)

    print(f"✅ Saved: {out_path}")
    print(out[["season","round","driver","incident","sc","vsc","red_flag"]].dropna().head(20).to_string(index=False))


if __name__ == "__main__":
    main()
