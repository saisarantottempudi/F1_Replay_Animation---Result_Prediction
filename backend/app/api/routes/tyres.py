from fastapi import APIRouter
from app.services.tyres import load_tyre_stints

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.get("/tyres/{season}/{round_no}/{session_code}")
def tyres(season: int, round_no: int, session_code: str):
    return load_tyre_stints(season, round_no, session_code)
