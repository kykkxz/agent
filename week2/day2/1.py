import pymysql
import pymysql.cursors
from typing import Any

DB_CONFIG: dict[str, Any] = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'test_db',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
    }

class DB_Utils:
    def __init__(self, config: dict[str, Any] = DB_CONFIG) -> None:
        self.config = config
        self.conn: Any | None = None
        self.cursor: Any | None = None

    def connect(self) -> tuple[Any, Any]:
        """建立数据库连接"""
        if self.conn is None or not self.conn.open:
            self.conn = pymysql.connect(**self.config)
            self.cursor = self.conn.cursor()
        assert self.conn is not None, "数据库连接建立失败"
        assert self.cursor is not None, "数据库游标获取失败"
        return self.conn, self.cursor
            
    def close(self) -> None:
        """关闭游标和连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn and self.conn.open:
            self.conn.close()

    def fetch_one(self, sql: str, args: tuple[Any, ...] | dict[str, Any]) -> dict[str, Any] | None:
        """查询单条记录"""
        _, cursor = self.connect()
        try:
            cursor.execute(sql, args)
            return cursor.fetchone()
        finally:
            self.close()

    def execute(self, sql: str, args: tuple[Any, ...] | dict[str, Any]) -> int:
        """执行单条命令，返回受影响的数据行数"""
        conn, cursor = self.connect()
        try:
            affected_rows = cursor.execute(sql, args)
            conn.commit()
            return affected_rows
        except Exception:
            conn.rollback()
            raise
        finally:
            self.close()
