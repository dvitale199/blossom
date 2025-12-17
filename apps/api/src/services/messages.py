from uuid import UUID

from supabase import Client

from src.models.schemas import Message


class MessageService:
    def __init__(self, db: Client):
        self.db = db

    async def get_recent_messages(
        self, conversation_id: UUID, limit: int = 20
    ) -> list[Message]:
        """Get recent messages from a conversation."""
        response = (
            self.db.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        # Reverse to get chronological order
        messages = [Message(**row) for row in reversed(response.data)]
        return messages

    async def store_message(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> Message:
        """Store a message in the database."""
        response = (
            self.db.table("messages")
            .insert({
                "conversation_id": str(conversation_id),
                "role": role,
                "content": content,
                "metadata": metadata or {},
            })
            .execute()
        )
        return Message(**response.data[0])

    async def update_conversation_timestamp(self, conversation_id: UUID) -> None:
        """Update the last_message_at timestamp."""
        self.db.table("conversations").update({
            "last_message_at": "now()"
        }).eq("id", str(conversation_id)).execute()

    async def update_message_metadata(
        self, message_id: UUID, metadata: dict
    ) -> Message:
        """Update message metadata (e.g., quiz responses)."""
        response = (
            self.db.table("messages")
            .update({"metadata": metadata})
            .eq("id", str(message_id))
            .execute()
        )
        return Message(**response.data[0])
