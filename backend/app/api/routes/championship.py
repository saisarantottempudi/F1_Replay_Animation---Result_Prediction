from fastapi import APIRouter, HTTPException
from app.services.sim_championship import simulate_season

router = APIRouter(prefix="/predict", tags=["predict"])


@router.get("/championship/{season}")
def predict_championship(season: int, sims: int = 300, upto_round: int | None = None):
    try:
        return simulate_season(season, n_sims=sims, top_round=upto_round)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
