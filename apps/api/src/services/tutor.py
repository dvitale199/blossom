import logging
import re
from typing import Any

import anthropic

from src.config import settings
from src.models.schemas import Message, Space

logger = logging.getLogger(__name__)

TUTOR_SYSTEM_PROMPT = """
You are Blossom, an AI tutor. Your job is to help the user genuinely understand
the topic they're learning—not just give them answers.

## How You Behave

**You teach through dialogue, not lectures.**
- Ask questions to understand what they know
- Explain concepts, then check understanding
- Use analogies and examples
- When they're confused, try a different angle

**You keep them thinking.**
- Don't just answer—ask "why do you think that?"
- Have them explain things back to you
- Challenge assumptions: "what would happen if...?"
- Praise effort and good reasoning, not just correct answers

**You validate understanding with quizzes.**
- After covering 2-3 concepts, check if it stuck
- Say "Let me see if this is solid" and ask 2-4 questions
- Questions should test understanding, not memorization
- Based on results: move on, or reteach differently

**You adapt.**
- If an explanation doesn't land, don't repeat it—try something else
- Notice when they're struggling vs. breezing through
- Adjust depth and pace accordingly

**You stay focused but not rigid.**
- Keep the learning goal in mind
- Tangents are okay if they help understanding
- Gently redirect if they go too far off track

## Quiz Format

When you quiz, use this format so the system can parse it:

<quiz>
<question id="1">
What would happen to X if Y changed?
<options>
A. First option
B. Second option
C. Third option
D. Fourth option
</options>
<answer>B</answer>
</question>
</quiz>

After they answer, evaluate and either:
- Confirm understanding and move on
- Identify the gap and reteach with a different approach

## What NOT To Do

- Don't lecture for paragraphs without engagement
- Don't accept "I get it" without demonstration
- Don't repeat failed explanations
- Don't be condescending or artificially cheerful
- Don't skip foundations to get to "interesting" stuff
- Don't give up if they're struggling—find another way in

## Remember

Your success is measured by whether they actually understand, not by how
much you covered or how smart you sounded.
"""


class TutorService:
    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def build_prompt(
        self,
        space: Space,
        messages: list[Message],
        quiz_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build the full system prompt with context."""
        formatted_messages = self._format_messages(messages[-20:])
        quiz_summary = self._format_quiz_summary(quiz_history or [])

        return f"""{TUTOR_SYSTEM_PROMPT}

<learning_context>
Topic: {space.topic}
Goal: {space.goal or "Explore and understand the topic"}

Recent conversation:
{formatted_messages}

Quiz history this session:
{quiz_summary}
</learning_context>

Continue the tutoring session. Remember where you left off.
"""

    async def generate_response(
        self,
        space: Space,
        messages: list[Message],
        user_message: str,
    ) -> str:
        """Generate a tutor response using Claude."""
        system_prompt = self.build_prompt(space, messages)

        # Build conversation history for Claude
        claude_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]
        claude_messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                messages=claude_messages,
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise TutorError("Failed to generate response") from e

    def extract_quiz_if_present(self, content: str) -> dict[str, Any] | None:
        """Extract quiz data from tutor response if present."""
        quiz_match = re.search(r"<quiz>(.*?)</quiz>", content, re.DOTALL)
        if not quiz_match:
            return None

        quiz_content = quiz_match.group(1)
        questions = []

        question_matches = re.findall(
            r'<question id="(\d+)">(.*?)</question>',
            quiz_content,
            re.DOTALL
        )

        for q_id, q_content in question_matches:
            # Extract question text
            text_match = re.search(r"^(.*?)<options>", q_content.strip(), re.DOTALL)
            question_text = text_match.group(1).strip() if text_match else q_content.strip()

            # Extract options
            options_match = re.search(r"<options>(.*?)</options>", q_content, re.DOTALL)
            options = []
            if options_match:
                options = [
                    opt.strip()
                    for opt in options_match.group(1).strip().split("\n")
                    if opt.strip()
                ]

            # Extract correct answer
            answer_match = re.search(r"<answer>(.*?)</answer>", q_content)
            correct_answer = answer_match.group(1).strip() if answer_match else ""

            questions.append({
                "id": f"q{q_id}",
                "text": question_text,
                "type": "mcq" if options else "short_response",
                "options": options,
                "correct_answer": correct_answer,
            })

        if not questions:
            return None

        return {
            "type": "quiz",
            "questions": questions,
            "status": "pending",
            "responses": [],
        }

    def _format_messages(self, messages: list[Message]) -> str:
        """Format messages for context injection."""
        if not messages:
            return "(No previous messages)"

        lines = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Tutor"
            # Truncate long messages
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _format_quiz_summary(self, quiz_history: list[dict[str, Any]]) -> str:
        """Format quiz history for context."""
        if not quiz_history:
            return "(No quizzes yet)"

        summaries = []
        for quiz in quiz_history[-3:]:  # Last 3 quizzes
            correct = sum(1 for r in quiz.get("responses", []) if r.get("is_correct"))
            total = len(quiz.get("questions", []))
            summaries.append(f"- Quiz: {correct}/{total} correct")
        return "\n".join(summaries)


class TutorError(Exception):
    """Error from tutor service."""
    pass
