# 요청 스키마 정의

from pydantic import BaseModel
from typing import List

class RecommendationRequest(BaseModel):
    goal: str
    preferred_parts: List[str]
    level: str
    frequency_per_week: int
    top_k: int = 5