from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.schemas import Conversation, Message, Space


@pytest.fixture
async def client():
    """Async test client for API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def sample_space(sample_user_id) -> Space:
    """Sample space for testing."""
    return Space(
        id=uuid4(),
        user_id=sample_user_id,
        name="Learn Python",
        topic="Python programming",
        goal="Understand the basics of Python",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={},
    )


@pytest.fixture
def sample_conversation(sample_space, sample_user_id) -> Conversation:
    """Sample conversation for testing."""
    return Conversation(
        id=uuid4(),
        space_id=sample_space.id,
        user_id=sample_user_id,
        started_at=datetime.now(),
        last_message_at=datetime.now(),
        summary=None,
        metadata={},
    )


@pytest.fixture
def sample_messages(sample_conversation) -> list[Message]:
    """Sample conversation messages for testing."""
    return [
        Message(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role="user",
            content="What is a variable in Python?",
            created_at=datetime.now(),
            metadata={},
        ),
        Message(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role="assistant",
            content="A variable in Python is like a container that stores data.",
            created_at=datetime.now(),
            metadata={},
        ),
    ]


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_supabase(mocker):
    """Mock Supabase client for testing."""
    mock_client = MagicMock()
    mocker.patch("src.db.supabase.get_supabase_client", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_anthropic(mocker):
    """Mock Anthropic client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is a test response from the tutor.")]
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def auth_headers(sample_user_id):
    """Auth headers with a test JWT token.

    Note: For actual route tests, you'll need to mock the auth dependency.
    This fixture provides the header format expected by the API.
    """
    return {"Authorization": f"Bearer test-token-{sample_user_id}"}
