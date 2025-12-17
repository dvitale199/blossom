from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from src.auth import User, get_current_user
from src.db.supabase import get_db
from src.models.schemas import (
    SendMessageRequest,
    MessageResponse,
    Message,
    QuizResponseRequest,
)
from src.services.messages import MessageService
from src.services.conversations import ConversationService
from src.services.spaces import SpaceService
from src.services.tutor import TutorService, TutorError

router = APIRouter(tags=["messages"])


def get_services(db: Client = Depends(get_db)) -> dict:
    return {
        "messages": MessageService(db),
        "conversations": ConversationService(db),
        "spaces": SpaceService(db),
        "tutor": TutorService(),
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    services: dict = Depends(get_services),
) -> MessageResponse:
    """Send a message and get tutor response."""
    msg_service: MessageService = services["messages"]
    conv_service: ConversationService = services["conversations"]
    space_service: SpaceService = services["spaces"]
    tutor: TutorService = services["tutor"]

    # 1. Verify conversation exists and belongs to user
    conversation = await conv_service.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 2. Get space for context
    space = await space_service.get_space(conversation.space_id, user.id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    # 3. Store user message
    await msg_service.store_message(
        conversation_id=conversation_id,
        role="user",
        content=body.content,
    )

    # 4. Get recent messages for context
    recent_messages = await msg_service.get_recent_messages(conversation_id)

    # 5. Generate tutor response
    try:
        tutor_response = await tutor.generate_response(
            space=space,
            messages=recent_messages,
            user_message=body.content,
        )
    except TutorError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # 6. Check for quiz in response
    quiz_data = tutor.extract_quiz_if_present(tutor_response)

    # 7. Store assistant message
    metadata = quiz_data if quiz_data else {}
    assistant_message = await msg_service.store_message(
        conversation_id=conversation_id,
        role="assistant",
        content=tutor_response,
        metadata=metadata,
    )

    # 8. Update conversation timestamp
    await msg_service.update_conversation_timestamp(conversation_id)

    return MessageResponse(
        message=assistant_message,
        has_quiz=quiz_data is not None,
    )


@router.post("/messages/{message_id}/quiz-response")
async def submit_quiz_response(
    message_id: UUID,
    body: QuizResponseRequest,
    user: User = Depends(get_current_user),
    services: dict = Depends(get_services),
) -> Message:
    """Submit quiz answers for a quiz message."""
    msg_service: MessageService = services["messages"]

    # Get the message (need to verify ownership through conversation)
    # For now, just update the metadata
    # TODO: Add proper ownership verification

    # Evaluate responses
    evaluated_responses = []
    for response in body.responses:
        # Find the question
        is_correct = False  # Will be evaluated based on correct_answer
        evaluated_responses.append({
            "question_id": response.question_id,
            "user_answer": response.user_answer,
            "is_correct": is_correct,  # TODO: Implement evaluation
        })

    # Update message metadata with responses
    updated_message = await msg_service.update_message_metadata(
        message_id,
        {
            "type": "quiz",
            "status": "completed",
            "responses": evaluated_responses,
        },
    )

    return updated_message
