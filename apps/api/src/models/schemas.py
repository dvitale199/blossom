from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Spaces
class CreateSpaceRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    topic: str = Field(..., min_length=1, max_length=500)
    goal: str | None = Field(None, max_length=1000)


class Space(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    topic: str
    goal: str | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


# Conversations
class Conversation(BaseModel):
    id: UUID
    space_id: UUID
    user_id: UUID
    started_at: datetime
    last_message_at: datetime
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationWithMessages(Conversation):
    messages: list["Message"]


# Messages
class Message(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str  # 'user', 'assistant', 'system'
    content: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    message: Message
    has_quiz: bool = False


# Quiz
class QuizResponse(BaseModel):
    question_id: str
    user_answer: str


class QuizResponseRequest(BaseModel):
    responses: list[QuizResponse]
