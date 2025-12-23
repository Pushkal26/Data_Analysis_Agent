from pydantic import BaseModel
from typing import List, Optional, Any

class ChatMessageBase(BaseModel):
    role: str
    content: str

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatSessionCreate(BaseModel):
    session_name: Optional[str] = "New Chat"

class ChatResponse(BaseModel):
    response: str
    trace: Optional[dict] = None

