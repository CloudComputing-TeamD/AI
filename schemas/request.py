# 요청 스키마 정의

from pydantic import BaseModel
from typing import List, Optional

class RecommendationRequest(BaseModel):
    goal: str
    preferred_parts: List[str]
    level: str
    top_k: Optional[int] = 5