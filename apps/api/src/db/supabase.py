from functools import lru_cache

from supabase import Client, create_client

from src.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """Get Supabase client (cached)."""
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError("Supabase URL and service key must be configured")

    return create_client(settings.supabase_url, settings.supabase_service_key)


def get_db() -> Client:
    """Dependency for getting database client."""
    return get_supabase_client()
