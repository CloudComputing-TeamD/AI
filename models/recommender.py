from db.mysql_connector import get_connection
from schemas.request import RecommendationRequest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from typing import Dict, Any

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

def fetch_exercises() -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM exercises")
        rows = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(rows)
    for col in ["target_parts", "equipment"]:
        df[col] = df[col].apply(lambda x: eval(x) if isinstance(x, str) else x)
    return df

def generate_recommendation(req: RecommendationRequest) -> Dict[str, Any]:
    df = fetch_exercises()

    # 벡터화 + 유사도 계산
    queries = [f"{p} {req.level} {t}" for p in req.preferred_parts for t in goal_to_types.get(req.goal, [])]
    vectorizer = TfidfVectorizer()
    doc_matrix = vectorizer.fit_transform(df["name"] + " " + df["type"] + " " + df["level"])
    user_vecs = vectorizer.transform(queries)
    user_profile = np.asarray(user_vecs.mean(axis=0))
    df["score"] = cosine_similarity(user_profile, doc_matrix).flatten()

    top_k = req.top_k or 5

    # 1. 각 부위별 최고 운동 1개씩 선택
    selected = []
    selected_ids = set()
    for part in req.preferred_parts:
        mask = df["target_parts"].apply(lambda parts: part in parts if isinstance(parts, list) else False)
        part_df = df[mask]
        if not part_df.empty:
            best = part_df.sort_values("score", ascending=False).iloc[0]
            selected.append(best)
            selected_ids.add(best["id"])

    # 2. 나머지 운동은 score 순 정렬 후 채우기
    remaining = df[~df["id"].isin(selected_ids)].sort_values("score", ascending=False)
    extra = remaining.head(top_k - len(selected))
    final = selected + extra.to_dict("records")

    # 3. sets/reps 추출
    rep_key = rep_ranges.get(req.goal, "3x12")
    rep_mapping = {
        "4x8": (4, 8),
        "3x15": (3, 15),
        "3x12": (3, 12)
    }
    sets, reps = rep_mapping.get(rep_key, (3, 12))

    # 4. routineItems 생성
    routine_items = []
    for i, row in enumerate(final):
        routine_items.append({
            "exerciseId": row["id"],
            "exerciseName": row["name"],
            "sets": sets,
            "reps": reps,
            "order": i + 1
        })

    # 5. 루틴 이름 생성
    if len(req.preferred_parts) == 1:
        routine_name = f"{req.preferred_parts[0]} 루틴"
    else:
        routine_name = f"{' + '.join(req.preferred_parts)} 루틴"

    return {
        "name": routine_name,
        "routineItems": routine_items
    }