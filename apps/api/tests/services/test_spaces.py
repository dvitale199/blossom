"""Tests for SpaceService."""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.models.schemas import CreateSpaceRequest, Space
from src.services.spaces import SpaceService


class TestCreateSpace:
    """Tests for space creation."""

    @pytest.mark.asyncio
    async def test_create_space_returns_space_with_id(self, sample_user_id):
        """Creating a space returns a Space with a generated ID."""
        mock_db = MagicMock()
        space_id = uuid4()
        now = datetime.now().isoformat()

        # Mock the Supabase response
        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": str(space_id),
                "user_id": str(sample_user_id),
                "name": "Learn Python",
                "topic": "Python programming",
                "goal": "Understand basics",
                "created_at": now,
                "updated_at": now,
                "metadata": {},
            }
        ]

        service = SpaceService(mock_db)
        request = CreateSpaceRequest(
            name="Learn Python",
            topic="Python programming",
            goal="Understand basics",
        )

        result = await service.create_space(sample_user_id, request)

        assert result.id == space_id
        assert result.user_id == sample_user_id
        assert result.name == "Learn Python"
        assert result.topic == "Python programming"

    @pytest.mark.asyncio
    async def test_create_space_includes_user_id(self, sample_user_id):
        """Created space is associated with the correct user."""
        mock_db = MagicMock()
        now = datetime.now().isoformat()

        mock_db.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": str(uuid4()),
                "user_id": str(sample_user_id),
                "name": "Test",
                "topic": "Testing",
                "goal": None,
                "created_at": now,
                "updated_at": now,
                "metadata": {},
            }
        ]

        service = SpaceService(mock_db)
        request = CreateSpaceRequest(name="Test", topic="Testing")

        await service.create_space(sample_user_id, request)

        # Verify insert was called with user_id
        insert_call = mock_db.table.return_value.insert.call_args
        assert insert_call[0][0]["user_id"] == str(sample_user_id)


class TestListSpaces:
    """Tests for listing spaces."""

    @pytest.mark.asyncio
    async def test_list_spaces_returns_user_spaces(self, sample_user_id):
        """List spaces returns only spaces belonging to the user."""
        mock_db = MagicMock()
        now = datetime.now().isoformat()

        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                "id": str(uuid4()),
                "user_id": str(sample_user_id),
                "name": "Space 1",
                "topic": "Topic 1",
                "goal": "Goal 1",
                "created_at": now,
                "updated_at": now,
                "metadata": {},
            },
            {
                "id": str(uuid4()),
                "user_id": str(sample_user_id),
                "name": "Space 2",
                "topic": "Topic 2",
                "goal": "Goal 2",
                "created_at": now,
                "updated_at": now,
                "metadata": {},
            },
        ]

        service = SpaceService(mock_db)
        result = await service.list_spaces(sample_user_id)

        assert len(result) == 2
        assert all(isinstance(s, Space) for s in result)
        assert all(s.user_id == sample_user_id for s in result)

    @pytest.mark.asyncio
    async def test_list_spaces_returns_empty_for_no_spaces(self, sample_user_id):
        """List spaces returns empty list when user has no spaces."""
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        service = SpaceService(mock_db)
        result = await service.list_spaces(sample_user_id)

        assert result == []


class TestGetSpace:
    """Tests for getting a single space."""

    @pytest.mark.asyncio
    async def test_get_space_returns_space(self, sample_user_id):
        """Get space returns the space if it belongs to user."""
        mock_db = MagicMock()
        space_id = uuid4()
        now = datetime.now().isoformat()

        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": str(space_id),
            "user_id": str(sample_user_id),
            "name": "My Space",
            "topic": "Learning",
            "goal": "Understand",
            "created_at": now,
            "updated_at": now,
            "metadata": {},
        }

        service = SpaceService(mock_db)
        result = await service.get_space(space_id, sample_user_id)

        assert result is not None
        assert result.id == space_id
        assert result.user_id == sample_user_id

    @pytest.mark.asyncio
    async def test_get_space_returns_none_for_wrong_user(self, sample_user_id):
        """Get space returns None if space doesn't belong to user."""
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data = None

        service = SpaceService(mock_db)
        result = await service.get_space(uuid4(), sample_user_id)

        assert result is None
