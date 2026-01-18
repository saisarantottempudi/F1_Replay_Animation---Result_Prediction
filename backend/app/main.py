from __future__ import annotations
from app.api.routes.tyres import router as tyres_router
from app.api.routes.strategy import router as strategy_router
from app.api.routes.tyre_degradation import router as tyre_deg_router

from fastapi import FastAPI
from app.api.routes.predict import router as predict_router
from app.api.routes.championship import router as championship_router
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

import fastf1

fastf1.Cache.enable_cache("../cache/fastf1")

app = FastAPI(
    title="F1 Replay & Prediction API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SeasonList(BaseModel):
    seasons: List[int]

class RaceInfo(BaseModel):
    round: int
    raceName: str

    date: str | None = None
class RaceList(BaseModel):
    season: int
    races: List[RaceInfo]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/options/seasons", response_model=SeasonList)
def seasons():
    """
    Return a stable list of seasons:
    - includes current year and next year for "upcoming predictions"
    - keeps older seasons available for replay
    """
    from datetime import datetime
    this_year = datetime.utcnow().year
    # Keep a reasonable history window; adjust if you want more
    start_year = 2018
    end_year = this_year + 1
    return SeasonList(seasons=list(range(start_year, end_year + 1)))



@app.get("/options/races/{season}", response_model=RaceList)
def races(season: int):
    """
    Return race list with optional ISO date (YYYY-MM-DD) if available.

    IMPORTANT:
    - For upcoming predictions we need dates to filter "future races".
    - FastF1 may fail to fetch schedules for future years depending on data availability/network/cache.
      In that case we fall back to an empty list (but NOT a 500).
    """
    try:
        schedule = fastf1.get_event_schedule(season)
    except Exception:
        # Don't crash the UI — just return empty.
        return RaceList(season=season, races=[])

    races: list[RaceInfo] = []

    for _, row in schedule.iterrows():
        # Round number (handle different column naming)
        rnd = row.get("RoundNumber", None)
        if rnd is None:
            rnd = row.get("Round", None)
        if rnd is None:
            continue

        try:
            round_num = int(rnd)
        except Exception:
            continue

        # Filter non-race placeholders (testing etc.)
        name = row.get("EventName", None) or row.get("Event", None) or "Unknown GP"
        name_s = str(name)
        if round_num <= 0:
            continue
        if "testing" in name_s.lower():
            continue

        # Date (best-effort)
        dt = row.get("EventDate", None) or row.get("Date", None)
        iso = None
        if dt is not None:
            try:
                # pandas.Timestamp -> python datetime -> ISO date
                iso = dt.to_pydatetime().date().isoformat()
            except Exception:
                try:
                    # already a date/datetime-like
                    iso = str(dt)[:10]
                except Exception:
                    iso = None

        races.append(RaceInfo(round=round_num, raceName=name_s, date=iso))

    races.sort(key=lambda x: x.round)
    return RaceList(season=season, races=races)



    races = []
    for _, row in schedule.iterrows():
        # Round
        rnd = None
        if "RoundNumber" in row:
            rnd = row.get("RoundNumber")
        elif "Round" in row:
            rnd = row.get("Round")
        if rnd is None:
            continue

        # Name
        name = None
        if "EventName" in row:
            name = row.get("EventName")
        elif "Event" in row:
            name = row.get("Event")
        if not name:
            name = "Unknown GP"

        # Date
        dt = None
        if "EventDate" in row:
            dt = row.get("EventDate")
        elif "Date" in row:
            dt = row.get("Date")

        date_iso = None
        try:
            if dt is not None:
                # pandas Timestamp or datetime
                if hasattr(dt, "date"):
                    date_iso = str(dt.date())
                else:
                    date_iso = str(dt)
                if " " in date_iso:
                    date_iso = date_iso.split(" ")[0]
        except Exception:
            date_iso = None

        races.append({"round": int(rnd), "raceName": str(name), "date": date_iso})

    races.sort(key=lambda x: x["round"])
    return {"season": season, "races": races}

class SessionList(BaseModel):
    season: int
    round: int
    sessions: List[str]

@app.get("/options/sessions/{season}/{round}", response_model=SessionList)
def sessions(season: int, round: int):
    # Standard weekend sessions; we'll upgrade to Sprint-aware soon
    base = ["FP1", "FP2", "FP3", "Q", "R"]
    return SessionList(season=season, round=round, sessions=base)




from app.services.weather_evolution import load_weather_and_tei

@app.get("/analysis/weather-evolution/{season}/{round}/{session}")
def weather_evolution(season: int, round: int, session: str):
    return load_weather_and_tei(season, round, session)

app.include_router(tyres_router)
app.include_router(strategy_router)
app.include_router(tyre_deg_router)

app.include_router(predict_router)
app.include_router(championship_router)
