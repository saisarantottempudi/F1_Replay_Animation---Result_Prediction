from fastapi import APIRouter, HTTPException
from app.services.predict_results import predict_race, predict_quali

router = APIRouter(prefix="/predict", tags=["predict"])


@router.get("/race/{season}/{round_no}")
def predict_race_endpoint(season: int, round_no: int, topk: int = 3):
    try:
        return predict_race(season, round_no, topk=topk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quali/{season}/{round_no}")
def predict_quali_endpoint(season: int, round_no: int, topk: int = 3):
    try:
        return predict_quali(season, round_no, topk=topk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
