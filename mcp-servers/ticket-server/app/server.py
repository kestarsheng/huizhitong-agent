from mcp.server.fastmcp import FastMCP

mcp = FastMCP("huizhitong-ticket")

_TICKETS: dict[str, dict[str, object]] = {}
_SEQUENCE = 1000
_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}


def _next_ticket_id() -> str:
    global _SEQUENCE
    _SEQUENCE += 1
    return f"TK-{_SEQUENCE}"


@mcp.tool()
def create_ticket(subject: str, description: str, priority: str = "MEDIUM", customer_id: str = "") -> dict:
    """创建售后工单，返回工单号、优先级与初始状态。"""
    if not subject.strip() or not description.strip():
        return {"created": False, "message": "工单主题和描述不能为空"}
    normalized = priority.upper()
    if normalized not in _PRIORITIES:
        return {"created": False, "message": f"优先级仅支持 {sorted(_PRIORITIES)}"}
    ticket_id = _next_ticket_id()
    ticket = {
        "ticket_id": ticket_id,
        "subject": subject.strip(),
        "description": description.strip(),
        "priority": normalized,
        "customer_id": customer_id.strip(),
        "status": "OPEN",
    }
    _TICKETS[ticket_id] = ticket
    return {"created": True, **ticket}


@mcp.tool()
def query_ticket(ticket_id: str) -> dict:
    """按工单号查询工单详情。"""
    ticket = _TICKETS.get(ticket_id)
    if ticket is None:
        return {"found": False, "ticket_id": ticket_id, "message": "未找到工单"}
    return {"found": True, **ticket}


if __name__ == "__main__":
    mcp.run(transport="stdio")
