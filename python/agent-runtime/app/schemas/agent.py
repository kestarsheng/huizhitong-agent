from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    agent_type: str = Field(min_length=1, max_length=100)
    conversation_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=10000)
    user_id: int | None = None
    tenant_id: int | None = None
    stream: bool = False


class AgentRunResponse(BaseModel):
    conversation_id: str
    agent_type: str
    status: str
    answer: str

