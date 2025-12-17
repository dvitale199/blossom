from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from src.db.supabase import get_db
from supabase import Client


security = HTTPBearer()


class User(BaseModel):
    id: UUID
    email: str | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Client = Depends(get_db),
) -> User:
    """Validate JWT token and return current user."""
    token = credentials.credentials

    try:
        # Verify the token with Supabase
        response = db.auth.get_user(token)
        if response.user:
            return User(
                id=UUID(response.user.id),
                email=response.user.email,
            )
    except Exception:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
