from __future__ import annotations

from typing import Any, Dict, List
import fastf1

# Cache so FastF1 doesn't re-download every time
fastf1.Cache.enable_cache("cache")

# FastF1 compound names vary a bit; normalize them
def normalize_compound(raw: str) -> str:
    s = (raw or "").upper().strip()
    if "SOFT" in s:
        return "SOFT"
    if "MED" in s:
        return "MEDIUM"
    if "HARD" in s:
        return "HARD"
    if "INTER" in s:
        return "INTERMEDIATE"
    if "WET" in s:
        return "WET"
    return "UNKNOWN"


def load_tyre_stints(season: int, round_no: int, session_code: str) -> Dict[str, Any]:
    """
    Returns per-driver tyre stints with compound + lap ranges + pit laps.
    Works best for Race (R), but also usable for practice/qualifying if tyre data exists.
    """
    session = fastf1.get_session(season, round_no, session_code)
    session.load(telemetry=False, weather=False, messages=False)

    laps = session.laps
    if laps is None or laps.empty:
        return {
            "season": season,
            "round": round_no,
            "session": session_code,
            "drivers": [],
            "message": "No lap data available for this session",
        }

    # Keep only rows with driver + lap number
    cols = [c for c in ["Driver", "LapNumber", "Compound", "TyreLife", "PitInTime", "PitOutTime"] if c in laps.columns]
    laps = laps[cols].dropna(subset=["Driver", "LapNumber"]).copy()

    drivers_out: List[Dict[str, Any]] = []

    for drv in sorted(laps["Driver"].unique()):
        d = laps[laps["Driver"] == drv].sort_values("LapNumber").copy()

        # Compound fallback if missing
        if "Compound" not in d.columns:
            d["Compound"] = "UNKNOWN"

        d["CompoundNorm"] = d["Compound"].astype(str).map(normalize_compound)

        stints: List[Dict[str, Any]] = []
        current = None

        for _, row in d.iterrows():
            lap_no = int(row["LapNumber"])
            comp = row["CompoundNorm"]

            pit_in = bool("PitInTime" in d.columns and row.get("PitInTime") is not None)
            # Start new stint if compound changes OR we have no stint yet
            if current is None or comp != current["compound"]:
                if current is not None:
                    stints.append(current)
                current = {
                    "compound": comp,
                    "lap_start": lap_no,
                    "lap_end": lap_no,
                    "pit_lap": None,
                }
            else:
                current["lap_end"] = lap_no

            # Mark pit lap if present (race sessions)
            if pit_in and current is not None:
                current["pit_lap"] = lap_no

        if current is not None:
            stints.append(current)

        drivers_out.append(
            {
                "driver": drv,
                "stints": stints,
                "total_laps": int(d["LapNumber"].max()),
            }
        )

    return {
        "season": season,
        "round": round_no,
        "session": session_code,
        "drivers": drivers_out,
        "message": "Tyre stints extracted (v1)",
    }
