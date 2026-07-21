from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, text
from sqlalchemy.engine import Engine



DB_NAME = "student_db"

server_engine: Engine = create_engine(
    "mysql+pymysql://root:123456@localhost:3306/",
    isolation_level="AUTOCOMMIT",
)

with server_engine.connect() as conn:
    conn.execute(text(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    ))


