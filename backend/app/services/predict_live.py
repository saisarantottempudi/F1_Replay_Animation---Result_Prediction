"""
Thin wrapper used by sim_championship.py.

This module intentionally adapts to the existing predictor used by:
  app/api/routes/predict.py

Auto-detected source:
  from app.services.predict_results import predict_race
"""
from __future__ import annotations
from typing import Any, Dict

from app.services.predict_results import predict_race as _predict_race_impl


def predict_race_live(season: int, round_no: int, topk: int = 20) -> Dict[str, Any]:
    """
    Returns a dict shaped like the /predict/race endpoint output (at least containing 'all').
    We call the underlying predictor with best-effort signature matching.
    """
    # Try common call signatures (named args first, then positional fallbacks)
    try:
        return _predict_race_impl(season=season, round_no=round_no, topk=topk)
    except TypeError:
        pass

    try:
        return _predict_race_impl(season=season, round_no=round_no)
    except TypeError:
        pass

    try:
        return _predict_race_impl(season, round_no, topk)
    except TypeError:
        pass

    # Final fallback
    return _predict_race_impl(season, round_no)
