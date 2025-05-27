## 목표
- 사용자의 운동 목표(goal), 주당 운동 횟수(frequency_per_week), 선호 부위(preferred_parts), 난이도(level)를 입력으로 받아 RDS에서 운동 정보를 읽어와, content-based filtering으로 1주일간의 운동 루틴을 추천.


## 전체 동작 흐름 예시
1. 사용자 입력(Flutter 앱)
'''
{
  "goal": "muscle_gain",
  "preferred_parts": ["가슴", "등", "하체"],
  "level": "beginner",
  "frequency_per_week": 3,
  "top_k": 4
}
'''

2. Flutter → Spring Boot → ELB → Private EC2 (FastAPI 호출)
- Flutter → Spring Boot 서버로 요청
- Spring Boot 서버는 ELB를 통해 private subnet 내 AI 서버로 POST 요청 전송
'''
POST http://ai-ec2-private-ip:8000/recommend
Content-Type: application/json
'''

3. AI 서버 로직(FastAPI + Recommender)
3-1. 요청 검증 및 파라미터 분배
- preferred_parts: ["가슴", "등", "하체"]
- frequency_per_week: 3 → 일주일 루틴을 3일로 나눔
'''
bins = [["가슴"], ["등"], ["하체"]]
'''

3-2. 운동 쿼리 벡터화
- 사용자의 goal "muscle_gain" → 추천 타입: ["strength"]
- preferred_parts × goal type 조합으로 문장 생성
'''
"가슴 beginner strength", "등 beginner strength", "하체 beginner strength"
'''
- 이 문장들을 TfidfVectorizer로 벡터화하여 평균 내 user profile vector 생성

4. RDS(MySQL)에서 운동 목록 로드드
- exercises 테이블에서 아래 필드를 SELECT
'''
SELECT id, name, target_parts, equipment, level, type, youtube FROM exercises
'''
- Pandas DataFrame으로 불러옴

5. Content-Based Filtering
- RDS에서 불러온 각 운동 row와 user profile vector 간 cosine similarity 계산
- 각 운동에 score 부여 → 높은 점수 기준으로 필터링

6. 루틴 구성: 요일별로 나눠 추천
'''
"Day1": {
  "target_parts": ["가슴"],
  "exercises": [
    {
      "id": 1,
      "name": "푸시업",
      "target_parts": ["가슴"],
      "equipment": ["맨몸"],
      "level": "beginner",
      "type": "strength",
      "youtube": "https://youtu.be/example1",
      "sets": "4x8",
      "score": 0.9234
    },
    ...
  ]
}
'''

7. 결과 반환(FastAPI → Spring Boot → Flutter)
- FastAPI가 JSON 형태로 루틴 결과 반환
'''
{
  "schedule": {
    "Day1": {...},
    "Day2": {...},
    "Day3": {...}
  }
}
'''