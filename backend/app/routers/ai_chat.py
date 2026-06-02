from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.llm_service import chat as llm_chat

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    msgs = [m.model_dump() for m in body.messages]
    result = await llm_chat(msgs, db, user.tenant_id, user.id)
    return ChatResponse(**result)
