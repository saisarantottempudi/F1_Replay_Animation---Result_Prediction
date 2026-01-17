from typing import Dict, Any
import random
import numpy as np

# Optional dependency (only required for full mode)
try:
    from app.services.predict_live import predict_race_live
except ModuleNotFoundError:
    predict_race_live = None

import fastf1
from collections import defaultdict


def simulate_season(
    season: int,
    sims: int = 300,
    upto_round: int | None = None,
    mode: str = "fast",
) -> Dict[str, Any]:
    """
    Simulate a full championship.

    mode:
      - fast: expected-points approximation (no per-race sampling)
      - full: Monte Carlo race-by-race simulation (requires predict_live)
    """

    # Cap sims defensively
    if mode == "fast":
        sims = min(int(sims), 50)
    elif mode == "full":
        sims = int(sims)
    else:
        sims = min(int(sims), 100)

    if mode == "full" and predict_race_live is None:
        raise RuntimeError("Full mode requires app.services.predict_live")

    return _simulate_season_impl(
        season=season,
        n_sims=sims,
        upto_round=upto_round,
        mode=mode,
    )


def _simulate_season_impl(
    season: int,
    n_sims: int = 300,
    upto_round: int | None = None,
    mode: str = "fast",
) -> Dict[str, Any]:

    schedule = fastf1.get_event_schedule(season)

    # Filter race events only
    races = schedule[schedule["EventFormat"] != "testing"]

    if upto_round is not None:
        races = races[races["RoundNumber"] <= upto_round]

    rounds = int(races["RoundNumber"].max())

    driver_titles = defaultdict(int)
    constructor_titles = defaultdict(int)

    if mode == "fast":
        return _simulate_fast_expected_points(season, races, upto_round)

    # -------- FULL MONTE CARLO MODE --------
    for _ in range(n_sims):
        driver_points = defaultdict(float)
        team_points = defaultdict(float)

        for _, row in races.iterrows():
            rnd = int(row["RoundNumber"])

            preds = predict_race_live(season, rnd)

            for i, d in enumerate(preds["all"]):
                pts = _points_for_position(i + 1)
                driver_points[d["driver"]] += pts
                team_points[d["team"]] += pts

        champ_driver = max(driver_points, key=driver_points.get)
        champ_team = max(team_points, key=team_points.get)

        driver_titles[champ_driver] += 1
        constructor_titles[champ_team] += 1

    return {
        "season": season,
        "mode": mode,
        "rounds_simulated": rounds,
        "driver_champion": [
            {"driver": k, "prob": v / n_sims}
            for k, v in sorted(driver_titles.items(), key=lambda x: -x[1])
        ],
        "constructor_champion": [
            {"team": k, "prob": v / n_sims}
            for k, v in sorted(constructor_titles.items(), key=lambda x: -x[1])
        ],
        "n_sims": n_sims,
    }


def _simulate_fast_expected_points(season, races, upto_round=None):
    """
    Fast approximation using expected race probabilities.
    """
    from app.services.predict_live import predict_race_live

    driver_points = defaultdict(float)
    team_points = defaultdict(float)

    for _, row in races.iterrows():
        rnd = int(row["RoundNumber"])
        preds = predict_race_live(season, rnd)

        for i, d in enumerate(preds["all"]):
            pts = _points_for_position(i + 1)
            driver_points[d["driver"]] += pts * d["p_win"]
            team_points[d["team"]] += pts * d["p_win"]

    return {
        "season": season,
        "mode": "fast",
        "driver_champion": sorted(
            [{"driver": k, "expected_points": v} for k, v in driver_points.items()],
            key=lambda x: -x["expected_points"],
        ),
        "constructor_champion": sorted(
            [{"team": k, "expected_points": v} for k, v in team_points.items()],
            key=lambda x: -x["expected_points"],
        ),
    }


def _points_for_position(pos: int) -> int:
    points = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
    return points[pos - 1] if pos <= len(points) else 0
