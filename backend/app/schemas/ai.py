from typing import Any, Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ToolTrace(BaseModel):
    name: str
    args: dict[str, Any]
    result_preview: str  # short, ~200 chars


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolTrace]
