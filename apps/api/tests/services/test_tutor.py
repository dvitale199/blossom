"""Tests for TutorService."""

import pytest

from src.services.tutor import TutorService


class TestExtractQuiz:
    """Tests for quiz extraction from tutor responses."""

    def test_extract_quiz_parses_valid_format(self, sample_space, sample_messages):
        """Quiz extraction correctly parses valid quiz XML format."""
        tutor = TutorService(client=None)  # No API calls needed for extraction

        content = """Great explanation! Now let me check your understanding.

<quiz>
<question id="1">
What is the output of print(2 + 2)?
<options>
A. 2
B. 4
C. 22
D. Error
</options>
<answer>B</answer>
</question>
</quiz>

Take your time to answer!"""

        result = tutor.extract_quiz_if_present(content)

        assert result is not None
        assert result["type"] == "quiz"
        assert result["status"] == "pending"
        assert len(result["questions"]) == 1

        question = result["questions"][0]
        assert question["id"] == "q1"
        assert "output of print(2 + 2)" in question["text"]
        assert question["correct_answer"] == "B"
        assert len(question["options"]) == 4
        assert question["type"] == "mcq"

    def test_extract_quiz_returns_none_for_no_quiz(self):
        """Returns None when no quiz is present in content."""
        tutor = TutorService(client=None)

        content = """A variable in Python is like a container that stores data.
        You can think of it as a labeled box where you put values.
        For example: x = 5 creates a variable called x that holds the number 5."""

        result = tutor.extract_quiz_if_present(content)

        assert result is None

    def test_extract_quiz_handles_multiple_questions(self):
        """Quiz extraction handles multiple questions."""
        tutor = TutorService(client=None)

        content = """<quiz>
<question id="1">
What is 2 + 2?
<options>
A. 3
B. 4
</options>
<answer>B</answer>
</question>
<question id="2">
What is 3 * 3?
<options>
A. 6
B. 9
</options>
<answer>B</answer>
</question>
</quiz>"""

        result = tutor.extract_quiz_if_present(content)

        assert result is not None
        assert len(result["questions"]) == 2
        assert result["questions"][0]["id"] == "q1"
        assert result["questions"][1]["id"] == "q2"

    def test_extract_quiz_handles_malformed_xml(self):
        """Returns None for malformed quiz XML."""
        tutor = TutorService(client=None)

        content = """<quiz>
        This is not valid quiz format
        </quiz>"""

        result = tutor.extract_quiz_if_present(content)

        # Should return None since no valid questions found
        assert result is None


class TestBuildPrompt:
    """Tests for prompt building."""

    def test_build_prompt_includes_space_context(self, sample_space, sample_messages):
        """Prompt includes space topic and goal."""
        tutor = TutorService(client=None)

        prompt = tutor.build_prompt(sample_space, sample_messages)

        assert sample_space.topic in prompt
        assert sample_space.goal in prompt

    def test_build_prompt_includes_recent_messages(self, sample_space, sample_messages):
        """Prompt includes formatted recent messages."""
        tutor = TutorService(client=None)

        prompt = tutor.build_prompt(sample_space, sample_messages)

        # Check message content is in prompt
        assert "What is a variable in Python?" in prompt
        assert "container that stores data" in prompt

    def test_build_prompt_includes_tutor_instructions(self, sample_space, sample_messages):
        """Prompt includes core tutor instructions."""
        tutor = TutorService(client=None)

        prompt = tutor.build_prompt(sample_space, [])

        # Check key tutor behaviors are present
        assert "teach through dialogue" in prompt.lower()
        assert "quiz" in prompt.lower()


class TestFormatMessages:
    """Tests for message formatting helper."""

    def test_format_messages_returns_placeholder_for_empty(self, sample_space):
        """Returns placeholder text for empty messages."""
        tutor = TutorService(client=None)

        result = tutor._format_messages([])

        assert "No previous messages" in result

    def test_format_messages_truncates_long_content(self, sample_space, sample_conversation):
        """Truncates messages longer than 500 characters."""
        from datetime import datetime
        from uuid import uuid4

        from src.models.schemas import Message

        tutor = TutorService(client=None)

        long_message = Message(
            id=uuid4(),
            conversation_id=sample_conversation.id,
            role="user",
            content="x" * 600,  # 600 character message
            created_at=datetime.now(),
            metadata={},
        )

        result = tutor._format_messages([long_message])

        # Should be truncated with ...
        assert "..." in result
        assert len(result) < 700  # Less than original + formatting
