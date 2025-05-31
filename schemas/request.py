# 요청 스키마 정의

from pydantic import BaseModel
from typing import List, Optional

class RecommendationRequest(BaseModel):
    goal: str   # MUSCLE_GAIN, FAT_LOSS, MAINTENANCE
    preferred_parts: List[str]  # 어깨, 가슴, 등, 하체, 복부, 팔, 전신
    level: str  # BEGINNER, INTERMEDIATE, ADVANCED
    gender: str # MALE, FEMALE
    weight: int
    top_k: Optional[int] = 5