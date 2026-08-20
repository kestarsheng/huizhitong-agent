from mcp.server.fastmcp import FastMCP

import os
import sqlite3
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("huizhitong-ticket")

_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}
_DEFAULT_TMP = Path(os.environ.get("TEMP", os.path.expanduser("~"))) / "huizhitong-ticket"
_DATA_DIR = Path(os.getenv("TICKET_DATA_DIR", _DEFAULT_TMP))
_DB_PATH = _DATA_DIR / "tickets.db"


def _connect() -> sqlite3.Connection:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tickets (
            ticket_id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            customer_id TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL
        )"""
    )
    conn.commit()
    return conn


def _next_ticket_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(ticket_id, 4) AS INTEGER)) FROM tickets"
    ).fetchone()
    sequence = (row[0] if row and row[0] else 1000) + 1
    return f"TK-{sequence}"


@mcp.tool()
def create_ticket(subject: str, description: str, priority: str = "MEDIUM", customer_id: str = "") -> dict:
    """创建售后工单，返回工单号、优先级与初始状态。"""
    if not subject.strip() or not description.strip():
        return {"created": False, "message": "工单主题和描述不能为空"}
    normalized = priority.upper()
    if normalized not in _PRIORITIES:
        return {"created": False, "message": f"优先级仅支持 {sorted(_PRIORITIES)}"}
    ticket = {
        "ticket_id": "",
        "subject": subject.strip(),
        "description": description.strip(),
        "priority": normalized,
        "customer_id": customer_id.strip(),
        "status": "OPEN",
    }
    with _connect() as conn:
        ticket["ticket_id"] = _next_ticket_id(conn)
        conn.execute(
            "INSERT INTO tickets (ticket_id, subject, description, priority, customer_id, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ticket["ticket_id"], ticket["subject"], ticket["description"],
             ticket["priority"], ticket["customer_id"], ticket["status"]),
        )
    return {"created": True, **ticket}


@mcp.tool()
def query_ticket(ticket_id: str) -> dict:
    """按工单号查询工单详情。"""
    with _connect() as conn:
        row = conn.execute(
            "SELECT ticket_id, subject, description, priority, customer_id, status "
            "FROM tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()
    if row is None:
        return {"found": False, "ticket_id": ticket_id, "message": "未找到工单"}
    keys = ("ticket_id", "subject", "description", "priority", "customer_id", "status")
    return {"found": True, **dict(zip(keys, row))}


if __name__ == "__main__":
    mcp.run(transport="stdio")
