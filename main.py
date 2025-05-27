# FastAPI 엔트리포인트

from fastapi import FastAPI, HTTPException
from schemas.request import RecommendationRequest
from models.recommender import generate_recommendation
import uvicorn

app = FastAPI()

@app.post("/recommend")
def recommend_routine(req: RecommendationRequest):
    try:
        result = generate_recommendation(req)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)