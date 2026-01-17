from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import pandas as pd
import joblib

from app.services.features_live import build_features_for_event

MODELS_DIR = Path("models")
DATA_PATH = Path("data/ml/driver_event_table_v1_4_quali_pos.parquet")

_model_win = None
_model_race_top3 = None
_model_pole = None
_model_quali_top3 = None


def _load_models():
    global _model_win, _model_race_top3, _model_pole, _model_quali_top3
    if _model_win is None:
        _model_win = joblib.load(MODELS_DIR / "model_win_v1.joblib")
    if _model_race_top3 is None:
        _model_race_top3 = joblib.load(MODELS_DIR / "model_race_top3_v1.joblib")
    if _model_pole is None:
        _model_pole = joblib.load(MODELS_DIR / "model_pole_v1.joblib")
    if _model_quali_top3 is None:
        _model_quali_top3 = joblib.load(MODELS_DIR / "model_quali_top3_v1.joblib")


def _event_frame_from_parquet(season: int, round_no: int) -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    df = df.dropna(subset=["season", "round", "driver"])
    df["season"] = df["season"].astype(int)
    df["round"] = df["round"].astype(int)

    ev = df[(df["season"] == season) & (df["round"] == round_no)].copy()
    if ev.empty:
        raise KeyError("not_in_parquet")

    ev = ev.sort_values(["driver"]).drop_duplicates(subset=["driver"], keep="last")
    return ev


def _build_event_features(season: int, round_no: int) -> tuple[pd.DataFrame, str]:
    """
    Use parquet if available; otherwise live FastF1 builder.
    """
    try:
        return _event_frame_from_parquet(season, round_no), "parquet"
    except KeyError:
        return build_features_for_event(season, round_no), "live_fastf1"


def predict_race(season: int, round_no: int, topk: int = 3) -> Dict[str, Any]:
    _load_models()
    ev, source = _build_event_features(season, round_no)

    p_win = _model_win.predict_proba(ev)[:, 1]
    p_top3 = _model_race_top3.predict_proba(ev)[:, 1]

    out = pd.DataFrame({
        "driver": ev["driver"].astype(str).values,
        "team": ev["team"].astype(str).values if "team" in ev.columns else None,
        "p_win": p_win,
        "p_top3": p_top3,
        "grid_pos": ev["grid_pos"].values if "grid_pos" in ev.columns else None,
        "quali_best_s": ev["quali_best_s"].values if "quali_best_s" in ev.columns else None,
    }).sort_values("p_win", ascending=False)

    return {
        "season": season,
        "round": round_no,
        "source": source,
        "winner": out.iloc[0].to_dict(),
        "top3": out.head(topk).to_dict(orient="records"),
        "all": out.to_dict(orient="records"),
        "message": "Race predictions generated (v1)."
    }


def predict_quali(season: int, round_no: int, topk: int = 3) -> Dict[str, Any]:
    _load_models()
    ev, source = _build_event_features(season, round_no)

    p_pole = _model_pole.predict_proba(ev)[:, 1]
    p_top3 = _model_quali_top3.predict_proba(ev)[:, 1]

    out = pd.DataFrame({
        "driver": ev["driver"].astype(str).values,
        "team": ev["team"].astype(str).values if "team" in ev.columns else None,
        "p_pole": p_pole,
        "p_top3": p_top3,
        "quali_best_s": ev["quali_best_s"].values if "quali_best_s" in ev.columns else None,
    }).sort_values("p_pole", ascending=False)

    return {
        "season": season,
        "round": round_no,
        "source": source,
        "pole": out.iloc[0].to_dict(),
        "top3": out.head(topk).to_dict(orient="records"),
        "all": out.to_dict(orient="records"),
        "message": "Qualifying predictions generated (v1)."
    }
