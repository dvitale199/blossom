from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from supabase import Client

from src.auth import User, get_current_user
from src.db.supabase import get_db
from src.models.schemas import Space, CreateSpaceRequest
from src.services.spaces import SpaceService

router = APIRouter(tags=["spaces"])


def get_space_service(db: Client = Depends(get_db)) -> SpaceService:
    return SpaceService(db)


@router.get("/spaces")
async def list_spaces(
    user: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_service),
) -> list[Space]:
    """List all spaces for the current user."""
    return await service.list_spaces(user.id)


@router.get("/spaces/{space_id}")
async def get_space(
    space_id: UUID,
    user: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_service),
) -> Space:
    """Get a specific space."""
    space = await service.get_space(space_id, user.id)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space {space_id} not found")
    return space


@router.post("/spaces", status_code=201)
async def create_space(
    body: CreateSpaceRequest,
    user: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_service),
) -> Space:
    """Create a new space."""
    return await service.create_space(user.id, body)


@router.delete("/spaces/{space_id}", status_code=204)
async def delete_space(
    space_id: UUID,
    user: User = Depends(get_current_user),
    service: SpaceService = Depends(get_space_service),
) -> None:
    """Delete a space."""
    deleted = await service.delete_space(space_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Space {space_id} not found")
