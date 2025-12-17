from uuid import UUID

from supabase import Client

from src.models.schemas import Conversation, ConversationWithMessages, Message


class ConversationService:
    def __init__(self, db: Client):
        self.db = db

    async def list_conversations(self, space_id: UUID, user_id: UUID) -> list[Conversation]:
        """List all conversations in a space."""
        response = (
            self.db.table("conversations")
            .select("*")
            .eq("space_id", str(space_id))
            .eq("user_id", str(user_id))
            .order("last_message_at", desc=True)
            .execute()
        )
        return [Conversation(**row) for row in response.data]

    async def get_conversation(
        self, conversation_id: UUID, user_id: UUID
    ) -> ConversationWithMessages | None:
        """Get a conversation with all messages."""
        # Get conversation
        conv_response = (
            self.db.table("conversations")
            .select("*")
            .eq("id", str(conversation_id))
            .eq("user_id", str(user_id))
            .single()
            .execute()
        )
        if not conv_response.data:
            return None

        # Get messages
        msg_response = (
            self.db.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at")
            .execute()
        )

        messages = [Message(**row) for row in msg_response.data]
        return ConversationWithMessages(**conv_response.data, messages=messages)

    async def create_conversation(self, space_id: UUID, user_id: UUID) -> Conversation:
        """Create a new conversation in a space."""
        response = (
            self.db.table("conversations")
            .insert({
                "space_id": str(space_id),
                "user_id": str(user_id),
            })
            .execute()
        )
        return Conversation(**response.data[0])

    async def get_or_create_active_conversation(
        self, space_id: UUID, user_id: UUID
    ) -> Conversation:
        """Get the most recent conversation or create one."""
        conversations = await self.list_conversations(space_id, user_id)
        if conversations:
            return conversations[0]
        return await self.create_conversation(space_id, user_id)
