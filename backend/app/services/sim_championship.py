from __future__ import annotations

from typing import Dict, Any, List, Tuple
import numpy as np
import fastf1

from app.services.predict_results import predict_race


# F1 points (modern)
POINTS_TOP10 = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]


def _sample_finish_order(drivers: List[str], p_win: np.ndarray) -> List[str]:
    """
    Simple probabilistic ordering:
    - Use p_win as "strength"
    - Convert to positive weights
    - Sample without replacement
    """
    w = np.clip(p_win, 1e-6, None)
    w = w / w.sum()
    order = []
    remaining = drivers[:]
    weights = w.copy()

    for _ in range(len(drivers)):
        idx = np.random.choice(len(remaining), p=weights)
        order.append(remaining.pop(idx))
        weights = np.delete(weights, idx)
        if len(weights) > 0:
            weights = weights / weights.sum()

    return order


def simulate_season(season: int, n_sims: int = 500, top_round: int | None = None) -> Dict[str, Any]:
    """
    Championship simulation:
    - gets schedule from FastF1
    - for each round: calls predict_race
    - samples finishing order using p_win distribution
    - assigns points for top10
    - aggregates driver + constructor points
    """

    schedule = fastf1.get_event_schedule(season)

    # ✅ Filter to actual race weekends (exclude testing / non-round entries)
    schedule = schedule.copy()
    schedule["RoundNumber"] = schedule["RoundNumber"].astype("Int64")

    # RoundNumber must exist and be >= 1 (removes pre-season testing which is often round 0)
    schedule = schedule[schedule["RoundNumber"].notna() & (schedule["RoundNumber"] >= 1)].copy()

    # Some seasons include non-championship items; ensure it looks like a race event
    if "EventName" in schedule.columns:
        schedule = schedule[~schedule["EventName"].str.contains("Testing", case=False, na=False)].copy()

    rounds = list(schedule["RoundNumber"].astype(int).values)

    if top_round is not None:
        rounds = [r for r in rounds if r <= int(top_round)]

    driver_titles = {}
    constructor_titles = {}

    for _ in range(n_sims):
        drv_points: Dict[str, int] = {}
        team_points: Dict[str, int] = {}
        driver_team: Dict[str, str] = {}

        for rnd in rounds:
            pred = predict_race(season, int(rnd), topk=3)
            all_rows = pred["all"]

            drivers = [r["driver"] for r in all_rows]
            teams = {r["driver"]: (r.get("team") or "UNKNOWN") for r in all_rows}
            p_win = np.array([r["p_win"] for r in all_rows], dtype=float)

            finish = _sample_finish_order(drivers, p_win)

            # assign points top10
            for pos, drv in enumerate(finish[:10]):
                pts = POINTS_TOP10[pos]
                drv_points[drv] = drv_points.get(drv, 0) + pts
                team = teams.get(drv, "UNKNOWN")
                driver_team[drv] = team
                team_points[team] = team_points.get(team, 0) + pts

        # champions of this simulation
        drv_champ = max(drv_points.items(), key=lambda x: x[1])[0] if drv_points else "UNKNOWN"
        team_champ = max(team_points.items(), key=lambda x: x[1])[0] if team_points else "UNKNOWN"

        driver_titles[drv_champ] = driver_titles.get(drv_champ, 0) + 1
        constructor_titles[team_champ] = constructor_titles.get(team_champ, 0) + 1

    # Convert to probabilities
    driver_odds = sorted(
        [{"driver": k, "prob": v / n_sims} for k, v in driver_titles.items()],
        key=lambda x: x["prob"],
        reverse=True,
    )
    constructor_odds = sorted(
        [{"team": k, "prob": v / n_sims} for k, v in constructor_titles.items()],
        key=lambda x: x["prob"],
        reverse=True,
    )

    return {
        "season": season,
        "n_sims": n_sims,
        "rounds_simulated": rounds,
        "driver_champion_odds": driver_odds,
        "constructor_champion_odds": constructor_odds,
        "message": "Championship simulation complete (v1 Monte Carlo)."
    }
