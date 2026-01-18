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
    return SeasonList(seasons=list(range(2018, 2026)))

@app.get("/options/races/{season}", response_model=RaceList)
def races(season: int):
    try:
        schedule = fastf1.get_event_schedule(season)
    except Exception:
        return {"season": season, "races": []}

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
