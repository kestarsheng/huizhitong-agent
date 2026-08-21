from mcp.server.fastmcp import FastMCP

import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("huizhitong-ticket")

_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}
_STORAGE = os.getenv("TICKET_STORAGE", "sqlite").lower()
_PH = "?" if _STORAGE == "sqlite" else "%s"

_TABLE_SQL = """CREATE TABLE IF NOT EXISTS tickets (
    ticket_id VARCHAR(32) PRIMARY KEY,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    priority VARCHAR(16) NOT NULL,
    customer_id VARCHAR(64) NOT NULL DEFAULT '',
    status VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""
_INSERT_SQL = f"INSERT INTO tickets (ticket_id, subject, description, priority, customer_id, status) VALUES ({_PH}, {_PH}, {_PH}, {_PH}, {_PH}, {_PH})"
_SELECT_SQL = f"SELECT ticket_id, subject, description, priority, customer_id, status FROM tickets WHERE ticket_id = {_PH}"
_MAX_ID_CAST = "UNSIGNED" if _STORAGE == "mysql" else "INTEGER"
_MAX_ID_SQL = f"SELECT MAX(CAST(SUBSTR(ticket_id, 4) AS {_MAX_ID_CAST})) FROM tickets"


def _connect():
    """按 TICKET_STORAGE 返回 MySQL 或 SQLite 连接，并保证库表存在。"""
    if _STORAGE == "mysql":
        import pymysql
        host = os.getenv("TICKET_MYSQL_HOST", "localhost")
        port = int(os.getenv("TICKET_MYSQL_PORT", "3306"))
        user = os.getenv("TICKET_MYSQL_USER", "root")
        password = os.getenv("TICKET_MYSQL_PASSWORD", "root")
        database = os.getenv("TICKET_MYSQL_DATABASE", "huizhitong")
        bootstrap = pymysql.connect(host=host, port=port, user=user, password=password, charset="utf8mb4")
        with bootstrap.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` DEFAULT CHARACTER SET utf8mb4")
        bootstrap.close()
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset="utf8mb4", autocommit=True)
        _exec(conn, _TABLE_SQL)
        return conn
    default_tmp = Path(os.environ.get("TEMP", os.path.expanduser("~"))) / "huizhitong-ticket"
    data_dir = Path(os.getenv("TICKET_DATA_DIR", default_tmp))
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(data_dir / "tickets.db")
    _exec(conn, _TABLE_SQL)
    conn.commit()
    return conn


def _exec(conn, sql: str, params: tuple = ()) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
    finally:
        cursor.close()


def _query(conn, sql: str, params: tuple = ()) -> list[tuple]:
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        cursor.close()


@mcp.tool()
def create_ticket(subject: str, description: str, priority: str = "MEDIUM", customer_id: str = "") -> dict:
    """创建售后工单，返回工单号、优先级与初始状态。"""
    if not subject.strip() or not description.strip():
        return {"created": False, "message": "工单主题和描述不能为空"}
    normalized = priority.upper()
    if normalized not in _PRIORITIES:
        return {"created": False, "message": f"优先级仅支持 {sorted(_PRIORITIES)}"}
    with _connect() as conn:
        rows = _query(conn, _MAX_ID_SQL)
        sequence = (rows[0][0] if rows and rows[0] and rows[0][0] else 1000) + 1
        ticket_id = f"TK-{sequence}"
        _exec(conn, _INSERT_SQL, (
            ticket_id, subject.strip(), description.strip(), normalized, customer_id.strip(), "OPEN",
        ))
    return {"created": True, "ticket_id": ticket_id, "subject": subject.strip(), "description": description.strip(),
            "priority": normalized, "customer_id": customer_id.strip(), "status": "OPEN"}


@mcp.tool()
def query_ticket(ticket_id: str) -> dict:
    """按工单号查询工单详情。"""
    with _connect() as conn:
        rows = _query(conn, _SELECT_SQL, (ticket_id,))
        row = rows[0] if rows else None
    if row is None:
        return {"found": False, "ticket_id": ticket_id, "message": "未找到工单"}
    keys = ("ticket_id", "subject", "description", "priority", "customer_id", "status")
    return {"found": True, **dict(zip(keys, row))}


if __name__ == "__main__":
    mcp.run(transport="stdio")
