from __future__ import annotations
from app.api.routes.tyres import router as tyres_router

from fastapi import FastAPI
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
    schedule = fastf1.get_event_schedule(season)
    races: List[RaceInfo] = []

    for _, row in schedule.iterrows():
        round_num = int(row["RoundNumber"])
        event_name = str(row["EventName"])

        # Filter out testing/non-race placeholders
        if round_num <= 0:
            continue
        if "testing" in event_name.lower():
            continue

        races.append(RaceInfo(round=round_num, raceName=event_name))

    races.sort(key=lambda x: x.round)
    return RaceList(season=season, races=races)

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
