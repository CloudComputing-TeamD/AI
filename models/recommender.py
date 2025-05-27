from db.mysql_connector import get_connection
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import numpy as np
from itertools import cycle, islice
from typing import Dict, Any

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

def fetch_exercises():
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM exercises")
        rows = cursor.fetchall()
    conn.close()
    return pd.DataFrame(rows)

def generate_recommendation(req) -> Dict[str, Any]:
    df = fetch_exercises()

    # 리스트 타입 칼럼 역직렬화
    for col in ["target_parts", "equipment"]:
        df[col] = df[col].apply(lambda x: eval(x) if isinstance(x, str) else x)

    queries = [f"{p} {req.level} {t}" for p in req.preferred_parts for t in goal_to_types.get(req.goal, [])]
    vectorizer = TfidfVectorizer()
    doc_matrix = vectorizer.fit_transform(df["name"] + " " + df["type"] + " " + df["level"])
    user_vecs = vectorizer.transform(queries)
    user_profile = np.asarray(user_vecs.mean(axis=0))
    
    sims = cosine_similarity(user_profile, doc_matrix).flatten()
    df["score"] = sims

    days = req.frequency_per_week
    bins = [[part] for part in islice(cycle(req.preferred_parts), days)]

    schedule: Dict[str, Any] = {}
    for i, parts in enumerate(bins, start=1):
        recs = []
        for part in parts:
            base_types = goal_to_types.get(req.goal, [])
            fallback_types = base_types + ["strength"]

            mask = (
                df["target_parts"].apply(lambda x: isinstance(x, list) and part in x) &
                df["type"].isin(base_types)
            )
            candidates = df[mask].sort_values("score", ascending=False).drop_duplicates("name").head(req.top_k)

            if len(candidates) < req.top_k:
                fallback_mask = (
                    df["target_parts"].apply(lambda x: isinstance(x, list) and part in x) &
                    df["type"].isin(fallback_types)
                )
                extra = df[fallback_mask].sort_values("score", ascending=False).drop_duplicates("name")
                extra = extra[~extra["name"].isin(candidates["name"])]
                candidates = pd.concat([candidates, extra]).head(req.top_k)

            for _, row in candidates.iterrows():
                recs.append({
                    "id": row["id"],
                    "name": row["name"],
                    "target_parts": row["target_parts"],
                    "equipment": row["equipment"],
                    "level": row["level"],
                    "type": row["type"],
                    "youtube": row["youtube"],
                    "sets": rep_ranges[req.goal],
                    "score": float(row["score"])
                })

        schedule[f"Day{i}"] = {"target_parts": parts, "exercises": recs}

    return {"schedule": schedule}
