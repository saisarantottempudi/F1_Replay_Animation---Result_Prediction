from fastapi import APIRouter, HTTPException
from app.services.tyre_degradation import compute_tyre_degradation

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/tyre-degradation/{season}/{round_no}/{session_code}/{driver}")
def tyre_degradation(season: int, round_no: int, session_code: str, driver: str):
    try:
        return compute_tyre_degradation(season, round_no, session_code, driver.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
