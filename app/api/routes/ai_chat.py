from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.schemas.ai_chat import AiChatResponse, AiConversationResponse, AiConversationSummary, AiMessageCreate, AiPlanResponse
from app.services import ai_chat_service

router = APIRouter(prefix="/api/v1/ai", tags=["pace ai"])


def get_ai_provider() -> ai_chat_service.PaceAiProvider:
    return ai_chat_service.PaceAiProvider()


@router.get("/plan", response_model=AiPlanResponse)
def get_plan(user: Annotated[PaceUser, Depends(get_current_user)], db: Session = Depends(get_db)):
    return ai_chat_service.plan_status(db, user)


@router.get("/conversations", response_model=list[AiConversationSummary])
def conversations(user: Annotated[PaceUser, Depends(get_current_user)], db: Session = Depends(get_db)):
    return ai_chat_service.list_conversations(db, user)


@router.get("/conversations/{conversation_id}", response_model=AiConversationResponse)
def conversation(conversation_id: UUID, user: Annotated[PaceUser, Depends(get_current_user)], db: Session = Depends(get_db)):
    row, messages = ai_chat_service.get_conversation(db, user, conversation_id)
    return {"id": row.id, "title": row.title, "created_at": row.created_at, "updated_at": row.updated_at, "messages": messages}


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_conversation(conversation_id: UUID, user: Annotated[PaceUser, Depends(get_current_user)], db: Session = Depends(get_db)):
    ai_chat_service.delete_conversation(db, user, conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chat", response_model=AiChatResponse)
def chat(payload: AiMessageCreate, user: Annotated[PaceUser, Depends(get_current_user)],
         provider: Annotated[ai_chat_service.PaceAiProvider, Depends(get_ai_provider)], db: Session = Depends(get_db)):
    conversation, message, plan, safety = ai_chat_service.send_message(db, user, payload.message, payload.conversation_id, provider)
    return {"conversation": conversation, "message": message, "plan": plan, "safety_intervened": safety}
