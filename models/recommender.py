from db.mysql_connector import get_connection
from schemas.request import RecommendationRequest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from typing import Dict, Any
import pymysql.cursors  

# 목표별 반복 횟수 (sets x reps)
rep_ranges = {
    "muscle_gain": "4x8",
    "fat_loss": "3x15",
    "maintenance": "3x12"
}

goal_to_types = {
    "muscle_gain": ["strength"],
    "fat_loss": ["cardio", "HIIT"],
    "maintenance": ["strength", "cardio", "HIIT"]
}

# 사용자 특성 기반 weight 추정
def estimate_weight(base, level, goal, gender):
    level_factor = {"beginner": 0.5, "intermediate": 0.75, "advanced": 1.0}.get(level, 0.6)
    goal_factor = {"fat_loss": 0.7, "maintenance": 0.85, "muscle_gain": 1.0}.get(goal, 0.85)
    gender_factor = 0.8 if gender.lower() == "female" else 1.0
    return round(base * level_factor * goal_factor * gender_factor)

# DB에서 운동 정보 가져오기
def fetch_exercises() -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:  
        cursor.execute("SELECT * FROM exercises")
        rows = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(rows)

    # 문자열 컬럼 처리
    for col in ["target"]:
        df[col] = df[col].apply(lambda x: eval(x) if isinstance(x, str) else x)

    df["base_weight"] = df["base_weight"].fillna(20).astype(int)
    return df

# 추천 생성 함수
def generate_recommendation(req: RecommendationRequest) -> Dict[str, Any]:
    df = fetch_exercises()

    goal = req.goal.lower()
    level = req.level.lower()
    gender = req.gender.lower()

    # 유사도 계산용 TF-IDF 벡터 생성
    queries = [f"{p} {level} {t}" for p in req.preferred_parts for t in goal_to_types.get(goal, [])]
    vectorizer = TfidfVectorizer()
    doc_matrix = vectorizer.fit_transform(df["name"] + " " + df["type"] + " " + df["level"])
    user_vecs = vectorizer.transform(queries)
    user_profile = np.asarray(user_vecs.mean(axis=0))
    df["score"] = cosine_similarity(user_profile, doc_matrix).flatten()

    top_k = req.top_k or 5

    # 부위별 최고 운동 1개씩 선택
    selected = []
    selected_ids = set()
    for part in req.preferred_parts:
        mask = df["target"].apply(lambda parts: part in parts if isinstance(parts, list) else False)
        part_df = df[mask]
        if not part_df.empty:
            best = part_df.sort_values("score", ascending=False).iloc[0]
            selected.append(best)
            selected_ids.add(best["id"])

    # 나머지 운동은 score 기준 정렬
    remaining = df[~df["id"].isin(selected_ids)].sort_values("score", ascending=False)
    extra = remaining.head(top_k - len(selected))
    final = selected + extra.to_dict("records")

    # 반복 수 추출
    rep_key = rep_ranges.get(goal, "3x12")
    rep_mapping = {
        "4x8": (4, 8),
        "3x15": (3, 15),
        "3x12": (3, 12)
    }
    sets, reps = rep_mapping.get(rep_key, (3, 12))

    # routineItems 생성
    routine_items = []
    for i, row in enumerate(final):
        base_weight = row.get("base_weight", 20)
        weight = estimate_weight(base_weight, level, goal, gender)
        routine_items.append({
            "exerciseId": row["id"],
            "sets": sets,
            "reps": reps,
            "weight": weight,
            "order": i + 1
        })

    # 루틴 이름 생성
    if len(req.preferred_parts) == 1:
        routine_name = f"{req.preferred_parts[0]} 루틴"
    else:
        routine_name = f"{' + '.join(req.preferred_parts)} 루틴"

    return {
        "name": routine_name,
        "routineItems": routine_items
    }
