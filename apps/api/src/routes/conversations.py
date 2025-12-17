from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from src.auth import User, get_current_user
from src.db.supabase import get_db
from src.models.schemas import Conversation, ConversationWithMessages
from src.services.conversations import ConversationService

router = APIRouter(tags=["conversations"])


def get_conversation_service(db: Client = Depends(get_db)) -> ConversationService:
    return ConversationService(db)


@router.get("/spaces/{space_id}/conversations")
async def list_conversations(
    space_id: UUID,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> list[Conversation]:
    """List all conversations in a space."""
    return await service.list_conversations(space_id, user.id)


@router.post("/spaces/{space_id}/conversations", status_code=201)
async def create_conversation(
    space_id: UUID,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> Conversation:
    """Create a new conversation in a space."""
    return await service.create_conversation(space_id, user.id)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationWithMessages:
    """Get a conversation with all messages."""
    conversation = await service.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    return conversation
