# RDS(MySQL) 연결 모듈

import pymysql
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )