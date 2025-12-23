from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.services.chat_agent import ChatAgentService
from app.schemas.chat import ChatMessageCreate, ChatResponse, ChatSessionCreate

router = APIRouter()

@router.post("/session", response_model=dict)
async def create_chat_session(
    session_in: ChatSessionCreate,
    db: AsyncSession = Depends(deps.get_db)
):
    service = ChatAgentService(db)
    session = await service.create_session(session_in.session_name)
    return {"session_id": session.id, "name": session.session_name}

@router.post("/{session_id}/message", response_model=ChatResponse)
async def send_message(
    session_id: int,
    message_in: ChatMessageCreate,
    db: AsyncSession = Depends(deps.get_db)
):
    service = ChatAgentService(db)
    response = await service.process_message(session_id, message_in.content)
    return response

