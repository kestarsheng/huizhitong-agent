from typing import TypedDict


class AgentState(TypedDict, total=False):
    agent_type: str
    conversation_id: str
    tenant_id: int
    user_message: str
    intent: str
    answer: str
    status: str

