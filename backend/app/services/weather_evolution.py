from typing import Dict, Any
import fastf1
import pandas as pd


def load_weather_and_track_evolution(
    season: int,
    round: int,
    session_name: str
) -> Dict[str, Any]:
    """
    Load weather data and prepare Track Evolution placeholders
    """

    # Load session
    session = fastf1.get_session(season, round, session_name)
    session.load(weather=True)

    weather = session.weather_data

    if weather is None or weather.empty:
        return {
            "season": season,
            "round": round,
            "session": session_name,
            "weather": [],
            "track_evolution": [],
            "message": "No weather data available"
        }

    # Clean weather dataframe
    weather_df = weather.copy()
    weather_df["Time"] = weather_df["Time"].astype(str)

    weather_records = weather_df[[
        "Time",
        "AirTemp",
        "TrackTemp",
        "Rainfall",
        "WindSpeed",
        "WindDirection"
    ]].to_dict(orient="records")

    # Placeholder for Track Evolution Index (TEI)
    # We will compute this in the next step
    track_evolution = []

    return {
        "season": season,
        "round": round,
        "session": session_name,
        "weather": weather_records,
        "track_evolution": track_evolution,
        "message": "Weather data loaded successfully"
    }
