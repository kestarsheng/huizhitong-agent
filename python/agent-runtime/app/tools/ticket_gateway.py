from dataclasses import dataclass, field

from app.tools.mcp_ticket_gateway import McpTicketGateway

_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}


@dataclass
class TicketToolGateway:
    """工单工具调用边界，MCP 不可用时按本地实现降级。"""

    _tickets: dict[str, dict[str, object]] = field(default_factory=dict)
    _sequence: int = 1000

    def _next_ticket_id(self) -> str:
        self._sequence += 1
        return f"TK-{self._sequence}"

    def create(self, subject: str, description: str, priority: str = "MEDIUM", customer_id: str = "") -> dict:
        if not subject.strip() or not description.strip():
            return {"created": False, "message": "工单主题和描述不能为空"}
        normalized = priority.upper()
        if normalized not in _PRIORITIES:
            return {"created": False, "message": f"优先级仅支持 {sorted(_PRIORITIES)}"}
        ticket_id = self._next_ticket_id()
        ticket = {
            "ticket_id": ticket_id,
            "subject": subject.strip(),
            "description": description.strip(),
            "priority": normalized,
            "customer_id": customer_id.strip(),
            "status": "OPEN",
        }
        self._tickets[ticket_id] = ticket
        return {"created": True, **ticket}

    def query(self, ticket_id: str) -> dict:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return {"found": False, "ticket_id": ticket_id, "message": "未找到工单"}
        return {"found": True, **ticket}


ticket_gateway = TicketToolGateway()
mcp_ticket_gateway = McpTicketGateway()
