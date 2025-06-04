from db.mysql_connector import get_connection
from schemas.request import RecommendationRequest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from typing import Dict, Any
import pymysql.cursors  

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

def estimate_weight(base, level, goal, gender):
    level_factor = {"beginner": 0.5, "intermediate": 0.75, "advanced": 1.0}.get(level, 0.6)
    goal_factor = {"fat_loss": 0.7, "maintenance": 0.85, "muscle_gain": 1.0}.get(goal, 0.85)
    gender_factor = 0.8 if gender.lower() == "female" else 1.0
    return round(base * level_factor * goal_factor * gender_factor)

def fetch_exercises() -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM exercises")
        rows = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(rows)
    df["base_weight"] = df["base_weight"].fillna(20).astype(int)
    return df

def generate_recommendation(req: RecommendationRequest) -> Dict[str, Any]:
    df = fetch_exercises()

    goal = req.goal.lower()
    level = req.level.lower()
    gender = req.gender.lower()

    queries = [f"{p} {level} {t}" for p in req.preferred_parts for t in goal_to_types.get(goal, [])]
    vectorizer = TfidfVectorizer()
    doc_matrix = vectorizer.fit_transform(df["name"] + " " + df["type"] + " " + df["level"])
    user_vecs = vectorizer.transform(queries)
    user_profile = np.asarray(user_vecs.mean(axis=0))
    df["score"] = cosine_similarity(user_profile, doc_matrix).flatten()

    top_k = req.top_k or 5

    selected = []
    selected_ids = set()
    # 부위별 최고 운동 1개씩 선택
    for part in req.preferred_parts:
        mask = df["target"].apply(lambda target: part == target if isinstance(target, str) else part in target)
        part_df = df[mask]
        if not part_df.empty:
            best = part_df.sort_values("score", ascending=False).iloc[0]
            selected.append(best)
            selected_ids.add(best["exerciseId"])

    # 나머지 운동은 preferred_parts에 포함되는 부위만 필터링 후 score 기준 정렬
    remaining = df[~df["exerciseId"].isin(selected_ids)]
    remaining = remaining[remaining["target"].apply(lambda target: any(p == target if isinstance(target, str) else p in target for p in req.preferred_parts))]
    remaining = remaining.sort_values("score", ascending=False)

    extra = remaining.head(max(0, top_k - len(selected)))
    final = selected + extra.to_dict("records")

    rep_key = rep_ranges.get(goal, "3x12")
    rep_mapping = {
        "4x8": (4, 8),
        "3x15": (3, 15),
        "3x12": (3, 12)
    }
    sets, reps = rep_mapping.get(rep_key, (3, 12))

    routine_items = []
    for i, row in enumerate(final):
        base_weight = row.get("base_weight", 20)
        weight = estimate_weight(base_weight, level, goal, gender)
        routine_items.append({
            "exerciseId": int(row["exerciseId"]),
            "sets": int(sets),
            "reps": int(reps),
            "weight": int(weight),
            "order": int(i + 1),
            "image": row.get("image", "")
        })

    if len(req.preferred_parts) == 1:
        routine_name = f"{req.preferred_parts[0]} 루틴"
    else:
        routine_name = f"{' + '.join(req.preferred_parts)} 루틴"

    return {
        "name": routine_name,
        "routineItems": routine_items
    }