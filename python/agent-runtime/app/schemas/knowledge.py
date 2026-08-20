from pydantic import BaseModel, Field


class DocumentCreateRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    content: str = Field(min_length=1, max_length=100000)
    tenant_id: str = Field(default="default", min_length=1, max_length=100)


class DocumentSummary(BaseModel):
    document_id: str
    tenant_id: str
    chunk_count: int
