from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    parent_node_id: str | None = None
    branch_name: str | None = None


class SseEnvelope(BaseModel):
    event: str
    data: dict[str, Any]
