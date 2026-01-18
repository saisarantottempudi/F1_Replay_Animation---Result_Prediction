from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Any
import math

import pandas as pd
import fastf1


def _softmax(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    m = max(scores.values())
    exps = {k: math.exp(v - m) for k, v in scores.items()}
    s = sum(exps.values()) or 1.0
    return {k: exps[k] / s for k in exps}


def _safe_str(x: Any) -> str:
    try:
        return str(x)
    except Exception:
        return ""


def _is_data_not_available_error(e: Exception) -> bool:
    msg = _safe_str(e).lower()
    needles = [
        "has not been",
        "not been made available",
        "not available",
        "no data",
        "failed to load any schedule data",
        "cannot",
        "404",
    ]
    return any(n in msg for n in needles)


@dataclass
class DriverStrength:
    score: float
    team: str | None = None


@lru_cache(maxsize=16)
def _build_strength_from_season(season_ref: int) -> Dict[str, DriverStrength]:
    schedule = fastf1.get_event_schedule(season_ref)

    race_points: Dict[str, float] = {}
    quali_pos_sum: Dict[str, float] = {}
    quali_pos_n: Dict[str, int] = {}
    team_map: Dict[str, str] = {}

    for _, row in schedule.iterrows():
        rnd = row.get("RoundNumber", None)
        if rnd is None:
            continue
        try:
            rnd = int(rnd)
        except Exception:
            continue
        if rnd <= 0:
            continue

        # Race
        try:
            s_r = fastf1.get_session(season_ref, rnd, "R")
            s_r.load()
            res = getattr(s_r, "results", None)
            if res is not None and len(res) > 0:
                for _, rr in res.iterrows():
                    drv = _safe_str(rr.get("Abbreviation", "")).upper()
                    if not drv:
                        continue
                    pts = rr.get("Points", 0.0)
                    try:
                        pts = float(pts) if pts is not None else 0.0
                    except Exception:
                        pts = 0.0
                    race_points[drv] = race_points.get(drv, 0.0) + pts

                    team = rr.get("TeamName", None)
                    if team and drv not in team_map:
                        team_map[drv] = _safe_str(team)
        except Exception:
            pass

        # Quali
        try:
            s_q = fastf1.get_session(season_ref, rnd, "Q")
            s_q.load()
            qres = getattr(s_q, "results", None)
            if qres is not None and len(qres) > 0:
                for _, qq in qres.iterrows():
                    drv = _safe_str(qq.get("Abbreviation", "")).upper()
                    if not drv:
                        continue
                    pos = qq.get("Position", None)
                    try:
                        pos = float(pos)
                    except Exception:
                        continue
                    quali_pos_sum[drv] = quali_pos_sum.get(drv, 0.0) + pos
                    quali_pos_n[drv] = quali_pos_n.get(drv, 0) + 1

                    team = qq.get("TeamName", None)
                    if team and drv not in team_map:
                        team_map[drv] = _safe_str(team)
        except Exception:
            pass

    out: Dict[str, DriverStrength] = {}
    for drv, pts in race_points.items():
        out[drv] = DriverStrength(score=float(pts), team=team_map.get(drv))

    if not out:
        for drv, s in quali_pos_sum.items():
            n = quali_pos_n.get(drv, 0)
            if n <= 0:
                continue
            avg_pos = s / n
            out[drv] = DriverStrength(score=float(1.0 / max(avg_pos, 1.0)), team=team_map.get(drv))

    return out


def _fallback_predict(season: int, round_no: int, kind: str, topk: int = 3) -> Dict[str, Any]:
    season_ref = max(season - 1, 2018)
    strength = _build_strength_from_season(season_ref)

    scores = {drv: ds.score for drv, ds in strength.items() if ds.score is not None}
    probs = _softmax(scores)
    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[: max(topk, 3)]

    if kind == "race":
        winner_drv, pwin = ranked[0]
        return {
            "season": season,
            "round": round_no,
            "source": f"historical_baseline_{season_ref}",
            "winner": {
                "driver": winner_drv,
                "team": strength.get(winner_drv).team if winner_drv in strength else None,
                "p_win": float(pwin),
                "p_top3": float(sum(p for _, p in ranked[:3])),
                "grid_pos": None,
                "quali_best_s": None,
            },
            "top3": [
                {
                    "driver": drv,
                    "team": strength.get(drv).team if drv in strength else None,
                    "p_win": float(p) if i == 0 else 0.0,
                    "p_top3": float(p),
                    "grid_pos": None,
                    "quali_best_s": None,
                }
                for i, (drv, p) in enumerate(ranked[:3])
            ],
            "note": "Future session data not available; using historical baseline strength model.",
        }

    pole_drv, ppole = ranked[0]
    return {
        "season": season,
        "round": round_no,
        "source": f"historical_baseline_{season_ref}",
        "pole": {
            "driver": pole_drv,
            "team": strength.get(pole_drv).team if pole_drv in strength else None,
            "p_pole": float(ppole),
            "p_top3": float(sum(p for _, p in ranked[:3])),
            "quali_best_s": None,
        },
        "top3": [
            {
                "driver": drv,
                "team": strength.get(drv).team if drv in strength else None,
                "p_pole": float(p) if i == 0 else 0.0,
                "p_top3": float(p),
                "quali_best_s": None,
            }
            for i, (drv, p) in enumerate(ranked[:3])
        ],
        "note": "Future session data not available; using historical baseline strength model.",
    }


def predict_race(season: int, round_no: int, topk: int = 3) -> Dict[str, Any]:
    try:
        sess = fastf1.get_session(season, round_no, "R")
        sess.load()
        results = getattr(sess, "results", None)
        if results is None or len(results) == 0:
            return _baseline_quali(season, round_no, topk=topk)

        scores: Dict[str, float] = {}
        team_map: Dict[str, str] = {}

        for _, r in results.iterrows():
            drv = _safe_str(r.get("Abbreviation", "")).upper()
            if not drv:
                continue
            pos = r.get("Position", None)
            try:
                pos = float(pos)
            except Exception:
                continue
            scores[drv] = 1.0 / max(pos, 1.0)

            team = r.get("TeamName", None)
            if team and drv not in team_map:
                team_map[drv] = _safe_str(team)

        probs = _softmax(scores)
        ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        top = ranked[: max(topk, 3)]
        winner_drv, pwin = top[0]

        return {
            "season": season,
            "round": round_no,
            "source": "live_fastf1",
            "winner": {
                "driver": winner_drv,
                "team": team_map.get(winner_drv),
                "p_win": float(pwin),
                "p_top3": float(sum(p for _, p in top[:3])),
                "grid_pos": None,
                "quali_best_s": None,
            },
            "top3": [
                {
                    "driver": drv,
                    "team": team_map.get(drv),
                    "p_win": float(p) if i == 0 else 0.0,
                    "p_top3": float(p),
                    "grid_pos": None,
                    "quali_best_s": None,
                }
                for i, (drv, p) in enumerate(top[:3])
            ],
        }

    except Exception as e:
        if _is_data_not_available_error(e):
            return _fallback_predict(season, round_no, "race", topk=topk)
        raise


def predict_quali(season: int, round_no: int, topk: int = 3) -> Dict[str, Any]:
    try:
        sess = fastf1.get_session(season, round_no, "Q")
        sess.load()
        results = getattr(sess, "results", None)
        if results is None or len(results) == 0:
            return _baseline_quali(season, round_no, topk=topk)

        scores: Dict[str, float] = {}
        team_map: Dict[str, str] = {}

        for _, r in results.iterrows():
            drv = _safe_str(r.get("Abbreviation", "")).upper()
            if not drv:
                continue
            pos = r.get("Position", None)
            try:
                pos = float(pos)
            except Exception:
                continue
            scores[drv] = 1.0 / max(pos, 1.0)

            team = r.get("TeamName", None)
            if team and drv not in team_map:
                team_map[drv] = _safe_str(team)

        probs = _softmax(scores)
        ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
        top = ranked[: max(topk, 3)]
        pole_drv, ppole = top[0]

        return {
            "season": season,
            "round": round_no,
            "source": "live_fastf1",
            "pole": {
                "driver": pole_drv,
                "team": team_map.get(pole_drv),
                "p_pole": float(ppole),
                "p_top3": float(sum(p for _, p in top[:3])),
                "quali_best_s": None,
            },
            "top3": [
                {
                    "driver": drv,
                    "team": team_map.get(drv),
                    "p_pole": float(p) if i == 0 else 0.0,
                    "p_top3": float(p),
                    "quali_best_s": None,
                }
                for i, (drv, p) in enumerate(top[:3])
            ],
        }

    except Exception as e:
        if _is_data_not_available_error(e):
            return _fallback_predict(season, round_no, "quali", topk=topk)
        raise

# --- BASELINE_FALLBACK_START ---
from typing import Optional, Dict, Any, List, Tuple
import fastf1

def _get_event_name(season: int, round_no: int) -> Optional[str]:
    try:
        sch = fastf1.get_event_schedule(season)
    except Exception:
        return None
    for _, row in sch.iterrows():
        rnd = row.get("RoundNumber", row.get("Round", None))
        try:
            if rnd is not None and int(rnd) == int(round_no):
                name = row.get("EventName", row.get("Event", None))
                return str(name) if name else None
        except Exception:
            continue
    return None

def _find_round_by_event_name(season: int, event_name: str) -> Optional[int]:
    try:
        sch = fastf1.get_event_schedule(season)
    except Exception:
        return None
    target = (event_name or "").strip().lower()
    for _, row in sch.iterrows():
        name = row.get("EventName", row.get("Event", None))
        if not name:
            continue
        if str(name).strip().lower() == target:
            rnd = row.get("RoundNumber", row.get("Round", None))
            try:
                return int(rnd)
            except Exception:
                return None
    return None

def _hist_results(event_name: str, kind: str, year: int):
    rnd = _find_round_by_event_name(year, event_name)
    if rnd is None:
        return None
    try:
        ses = fastf1.get_session(year, rnd, kind)  # kind: "R" or "Q"
        ses.load(messages=False, weather=False)
        res = ses.results
        if res is None or len(res) == 0:
            return None
        rows = []
        for _, r in res.iterrows():
            abbr = r.get("Abbreviation")
            team = r.get("TeamName") or r.get("Team")
            pos = r.get("Position")
            if not abbr or pos is None:
                continue
            try:
                pos = int(pos)
            except Exception:
                continue
            rows.append({"abbr": str(abbr), "team": str(team) if team else "", "pos": pos})
        return rows if rows else None
    except Exception:
        return None

def _baseline_from_history(season: int, round_no: int, kind: str, topk: int = 3) -> Dict[str, Any]:
    event_name = _get_event_name(season, round_no) or ""
    if not event_name:
        return {"season": season, "round": round_no, "source": "baseline_history",
                "message": "No schedule/event name available yet for this season/round."}

    used = 0
    wins = {}
    top3 = {}
    team_of = {}

    for y in range(season - 1, max(season - 6, 2018), -1):
        rows = _hist_results(event_name, kind, y)
        if not rows:
            continue
        used += 1
        rows = sorted(rows, key=lambda x: x["pos"])

        # winner/pole
        w = rows[0]["abbr"]
        wins[w] = wins.get(w, 0) + 1

        # top3
        for r in rows[:3]:
            top3[r["abbr"]] = top3.get(r["abbr"], 0) + 1

        # team mapping
        for r in rows[:10]:
            if r["abbr"] not in team_of and r["team"]:
                team_of[r["abbr"]] = r["team"]

        if used >= 5:
            break

    if used == 0:
        return {"season": season, "round": round_no, "source": "baseline_history",
                "event": event_name, "message": f"No historical results found for {event_name}."}

    drivers = set(list(wins.keys()) + list(top3.keys()))
    ranked = []
    for d in drivers:
        p_win = wins.get(d, 0) / used
        p_t3  = top3.get(d, 0) / used
        ranked.append((d, p_win, p_t3))
    ranked.sort(key=lambda x: (x[1], x[2]), reverse=True)

    def pack(d, pwin, pt3):
        return {"driver": d, "team": team_of.get(d, ""), "p_win": float(pwin), "p_top3": float(pt3),
                "grid_pos": None, "quali_best_s": None}

    ranked = ranked[:max(topk, 3)]

    if kind == "R":
        return {
            "season": season, "round": round_no, "source": "baseline_history", "event": event_name,
            "winner": pack(*ranked[0]),
            "top3": [pack(*x) for x in ranked[:3]],
            "meta": {"years_used": used, "mode": "baseline"}
        }

    # Quali baseline: interpret win fraction as pole fraction
    pole_d, pole_p, pole_t3 = ranked[0]
    return {
        "season": season, "round": round_no, "source": "baseline_history", "event": event_name,
        "pole": {"driver": pole_d, "team": team_of.get(pole_d, ""), "p_pole": float(pole_p), "p_top3": float(pole_t3), "quali_best_s": None},
        "top3": [{"driver": d, "team": team_of.get(d, ""), "p_pole": float(pw), "p_top3": float(pt), "quali_best_s": None}
                 for (d,pw,pt) in ranked[:3]],
        "meta": {"years_used": used, "mode": "baseline"}
    }

def _baseline_race(season: int, round_no: int, topk: int = 3) -> Dict[str, Any]:
    return _baseline_from_history(season, round_no, kind="R", topk=topk)

def _baseline_quali(season: int, round_no: int, topk: int = 3) -> Dict[str, Any]:
    return _baseline_from_history(season, round_no, kind="Q", topk=topk)

# --- BASELINE_FALLBACK_END ---
