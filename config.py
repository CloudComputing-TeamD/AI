# .env 파일에 DB 정보 설정(EC2에 .env 파일 수동 복사)
"""
DB_HOST=your-db-hostname.rds.amazonaws.com
DB_USER=your_db_user
DB_PASSWORD=your_secure_password
DB_NAME=your_database_name
"""
import os
from dotenv import load_dotenv

load_dotenv() # .env 파일에서 환경 변수 불러오기

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
