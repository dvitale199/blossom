from uuid import UUID

from supabase import Client

from src.models.schemas import Space, CreateSpaceRequest


class SpaceService:
    def __init__(self, db: Client):
        self.db = db

    async def list_spaces(self, user_id: UUID) -> list[Space]:
        """List all spaces for a user."""
        response = (
            self.db.table("spaces")
            .select("*")
            .eq("user_id", str(user_id))
            .order("updated_at", desc=True)
            .execute()
        )
        return [Space(**row) for row in response.data]

    async def get_space(self, space_id: UUID, user_id: UUID) -> Space | None:
        """Get a specific space if it belongs to the user."""
        response = (
            self.db.table("spaces")
            .select("*")
            .eq("id", str(space_id))
            .eq("user_id", str(user_id))
            .single()
            .execute()
        )
        if response.data:
            return Space(**response.data)
        return None

    async def create_space(self, user_id: UUID, data: CreateSpaceRequest) -> Space:
        """Create a new space."""
        response = (
            self.db.table("spaces")
            .insert({
                "user_id": str(user_id),
                "name": data.name,
                "topic": data.topic,
                "goal": data.goal,
            })
            .execute()
        )
        return Space(**response.data[0])

    async def delete_space(self, space_id: UUID, user_id: UUID) -> bool:
        """Delete a space if it belongs to the user."""
        response = (
            self.db.table("spaces")
            .delete()
            .eq("id", str(space_id))
            .eq("user_id", str(user_id))
            .execute()
        )
        return len(response.data) > 0
