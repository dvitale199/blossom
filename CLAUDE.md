# CLAUDE.md

Quick reference for AI assistants working on Blossom.

## Project Overview

Blossom is an AI tutoring platform. Users chat with a tutor that teaches through dialogue, probes understanding, and validates learning via inline quizzes.

**Core thesis:** AI should make people smarter, not do their thinking for them.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 + shadcn/ui + Tailwind |
| Backend | FastAPI (Python 3.11+) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth |
| AI | Claude API (Anthropic) |
| Deployment | Vercel (web) + Cloud Run (api) |

## Project Structure

```
blossom/
├── apps/
│   ├── web/                 # Next.js frontend
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   ├── lib/             # Utilities, API client
│   │   └── hooks/           # Custom hooks
│   │
│   └── api/                 # FastAPI backend
│       └── src/
│           ├── main.py      # App entry
│           ├── config.py    # Settings
│           ├── routes/      # API endpoints
│           ├── services/    # Business logic
│           ├── models/      # Pydantic schemas
│           └── db/          # Database client
│
├── docs/                    # Documentation
└── tests/                   # Test files mirror src structure
```

## Development Commands

```bash
# Frontend (apps/web)
npm run dev          # Start dev server
npm run build        # Build for production
npm run test         # Run tests
npm run lint         # Lint code

# Backend (apps/api)
uvicorn src.main:app --reload    # Start dev server
pytest                           # Run tests
pytest --cov=src                 # Run with coverage
ruff check .                     # Lint
ruff format .                    # Format
```

## Code Conventions

### Python (Backend)

```python
# Use Pydantic for all request/response models
class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)

class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
    metadata: dict = Field(default_factory=dict)

# Async everywhere
async def send_message(conversation_id: UUID, body: SendMessageRequest) -> MessageResponse:
    ...

# Type hints required
def build_tutor_prompt(space: Space, messages: list[Message]) -> str:
    ...

# Dependency injection for auth
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    ...
```

### TypeScript (Frontend)

```typescript
// Types for all props
interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

// Use server components by default, 'use client' only when needed
// Prefer React Server Components for data fetching

// API calls via lib/api.ts
const response = await api.conversations.sendMessage(conversationId, { content });
```

## Database Schema (Core Tables)

```sql
spaces          -- Learning contexts (topic + goal)
conversations   -- Chat sessions within a space
messages        -- Individual messages (user/assistant)
                -- Quiz data stored in message.metadata
```

## Key Patterns

### Context Injection for Tutor

```python
def build_tutor_prompt(space: Space, messages: list[Message], quiz_history: list) -> str:
    return f"""
    {TUTOR_SYSTEM_PROMPT}
    
    <context>
    Topic: {space.topic}
    Goal: {space.goal}
    Recent messages: {format_messages(messages[-20:])}
    Quiz history: {format_quiz_summary(quiz_history)}
    </context>
    """
```

### Quiz in Message Metadata

```python
# Quiz stored as message metadata
message.metadata = {
    "type": "quiz",
    "questions": [...],
    "status": "pending" | "completed",
    "responses": [...]
}
```

### Error Handling

```python
# Use HTTPException with clear messages
raise HTTPException(
    status_code=404,
    detail=f"Conversation {conversation_id} not found"
)

# Catch Claude API errors gracefully
try:
    response = await client.messages.create(...)
except anthropic.APIError as e:
    logger.error(f"Claude API error: {e}")
    raise HTTPException(status_code=502, detail="AI service unavailable")
```

## Testing Approach

**Write tests first.** For every feature:

1. Write test that describes expected behavior
2. Run test (should fail)
3. Implement minimum code to pass
4. Refactor if needed
5. Repeat

```python
# Test file mirrors source structure
# src/services/tutor.py → tests/services/test_tutor.py

async def test_send_message_returns_tutor_response():
    # Arrange
    conversation = await create_test_conversation()
    
    # Act
    response = await send_message(conversation.id, "Hello")
    
    # Assert
    assert response.role == "assistant"
    assert len(response.content) > 0
```

## What NOT to Do

- Don't commit API keys or secrets
- Don't skip tests for "simple" changes
- Don't add dependencies without justification
- Don't write long functions (>30 lines is a smell)
- Don't ignore type errors
- Don't hardcode configuration

## Current Focus (v0)

Building the minimal chat-first tutor:

1. ✅ Chat with a tutor (smart system prompt)
2. ✅ Inline quizzes as validation checkpoints
3. ✅ Conversation persistence across sessions

NOT building yet:
- Knowledge map generation
- Mastery tracking calculations
- Conversation analysis pipelines
- Progress UI

See `docs/v0-mvp.md` for full scope.