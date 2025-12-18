"""Tests for message routes."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.auth import User
from src.main import app
from src.models.schemas import Conversation, Message, Space


# Override auth dependency for testing
async def mock_get_current_user():
    """Mock user for testing."""
    return User(id=uuid4(), email="test@example.com")


class TestSendMessageAuth:
    """Tests for authentication on send_message endpoint."""

    @pytest.mark.asyncio
    async def test_send_message_without_auth_returns_401(self, client):
        """Request without auth token returns 401."""
        response = await client.post(
            f"/api/conversations/{uuid4()}/messages",
            json={"content": "Hello"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_send_message_with_invalid_token_returns_401(self, client):
        """Request with invalid token returns 401."""
        response = await client.post(
            f"/api/conversations/{uuid4()}/messages",
            json={"content": "Hello"},
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401


class TestSendMessageFlow:
    """Tests for the full send_message flow with mocked dependencies."""

    @pytest.fixture
    def mock_services(self, sample_space, sample_conversation, sample_messages):
        """Create mock services for testing."""
        now = datetime.now()

        # Mock message service
        msg_service = MagicMock()
        msg_service.store_message = AsyncMock(
            return_value=Message(
                id=uuid4(),
                conversation_id=sample_conversation.id,
                role="assistant",
                content="This is the tutor response.",
                created_at=now,
                metadata={},
            )
        )
        msg_service.get_recent_messages = AsyncMock(return_value=sample_messages)
        msg_service.update_conversation_timestamp = AsyncMock()

        # Mock conversation service
        conv_service = MagicMock()
        conv_service.get_conversation = AsyncMock(return_value=sample_conversation)

        # Mock space service
        space_service = MagicMock()
        space_service.get_space = AsyncMock(return_value=sample_space)

        # Mock tutor service
        tutor_service = MagicMock()
        tutor_service.generate_response = AsyncMock(
            return_value="This is the tutor response."
        )
        tutor_service.extract_quiz_if_present = MagicMock(return_value=None)

        return {
            "messages": msg_service,
            "conversations": conv_service,
            "spaces": space_service,
            "tutor": tutor_service,
        }

    @pytest.mark.asyncio
    async def test_send_message_returns_assistant_response(
        self, sample_conversation, mock_services
    ):
        """Successfully sending a message returns assistant response."""
        from src.routes.messages import router, get_services
        from src.auth import get_current_user

        # Create a test app with overridden dependencies
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        test_user = User(id=sample_conversation.user_id, email="test@example.com")

        test_app.dependency_overrides[get_current_user] = lambda: test_user
        test_app.dependency_overrides[get_services] = lambda: mock_services

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/conversations/{sample_conversation.id}/messages",
                json={"content": "What is Python?"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["message"]["role"] == "assistant"
        assert data["has_quiz"] is False

    @pytest.mark.asyncio
    async def test_send_message_to_invalid_conversation_returns_404(self, mock_services):
        """Sending message to non-existent conversation returns 404."""
        from src.routes.messages import router, get_services
        from src.auth import get_current_user

        # Mock conversation not found
        mock_services["conversations"].get_conversation = AsyncMock(return_value=None)

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        test_user = User(id=uuid4(), email="test@example.com")

        test_app.dependency_overrides[get_current_user] = lambda: test_user
        test_app.dependency_overrides[get_services] = lambda: mock_services

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/conversations/{uuid4()}/messages",
                json={"content": "Hello"},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_send_message_with_quiz_response(
        self, sample_conversation, mock_services
    ):
        """Response containing quiz sets has_quiz to True."""
        from src.routes.messages import router, get_services
        from src.auth import get_current_user

        # Mock tutor returns quiz
        quiz_data = {
            "type": "quiz",
            "questions": [{"id": "q1", "text": "Test?", "options": [], "correct_answer": "A"}],
            "status": "pending",
            "responses": [],
        }
        mock_services["tutor"].extract_quiz_if_present = MagicMock(return_value=quiz_data)

        # Update the stored message to include quiz metadata
        mock_services["messages"].store_message = AsyncMock(
            return_value=Message(
                id=uuid4(),
                conversation_id=sample_conversation.id,
                role="assistant",
                content="<quiz>...</quiz>",
                created_at=datetime.now(),
                metadata=quiz_data,
            )
        )

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        test_user = User(id=sample_conversation.user_id, email="test@example.com")

        test_app.dependency_overrides[get_current_user] = lambda: test_user
        test_app.dependency_overrides[get_services] = lambda: mock_services

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/conversations/{sample_conversation.id}/messages",
                json={"content": "Quiz me"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["has_quiz"] is True
