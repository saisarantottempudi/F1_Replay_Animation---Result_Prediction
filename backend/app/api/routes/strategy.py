from fastapi import APIRouter, HTTPException
from app.services.strategy import compute_strategy_intelligence

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/strategy/{season}/{round_no}")
def strategy(season: int, round_no: int):
    try:
        return compute_strategy_intelligence(season, round_no)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
