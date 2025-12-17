# Blossom Development Guide

Guidelines for developing Blossom with AI assistance. Focused on what matters: TDD, incremental changes, and keeping the codebase healthy.

---

## Core Principles

### 1. Test First, Always

Every feature starts with a test. No exceptions.

```
1. Write a failing test that describes what you want
2. Run it (red)
3. Write minimum code to pass (green)
4. Refactor if needed
5. Commit
```

**Why:** AI generates plausible-looking code that may be subtly wrong. Tests catch this. Without tests, bugs accumulate silently.

### 2. Small, Atomic Changes

Each commit does one thing. Each PR is reviewable in 10 minutes.

**Good:**
- "Add Message model and schema"
- "Add POST /messages endpoint"
- "Add message persistence to database"

**Bad:**
- "Add messaging feature with database, API, and frontend"

**Why:** Small changes are easy to review, easy to test, easy to revert. Large changes hide bugs.

### 3. Verify Everything

AI-generated code is a hypothesis. Treat it as such.

- **Run the tests** after every change
- **Check the types** (`mypy`, TypeScript)
- **Lint the code** (`ruff`, `eslint`)
- **Try it manually** before calling it done

---

## TDD Workflow

### Backend (Python/FastAPI)

#### File Structure

```
apps/api/
├── src/
│   ├── routes/
│   │   └── messages.py
│   ├── services/
│   │   └── tutor.py
│   └── models/
│       └── schemas.py
└── tests/
    ├── routes/
    │   └── test_messages.py
    ├── services/
    │   └── test_tutor.py
    └── conftest.py          # Shared fixtures
```

#### Writing Tests

```python
# tests/services/test_tutor.py

import pytest
from src.services.tutor import TutorService

@pytest.fixture
def tutor_service():
    return TutorService()

class TestBuildPrompt:
    """Tests for prompt construction."""
    
    def test_includes_topic_and_goal(self, tutor_service):
        space = Space(topic="Python basics", goal="Learn fundamentals")
        
        prompt = tutor_service.build_prompt(space, messages=[])
        
        assert "Python basics" in prompt
        assert "Learn fundamentals" in prompt
    
    def test_includes_recent_messages(self, tutor_service):
        space = Space(topic="Python", goal="Learn")
        messages = [
            Message(role="user", content="What is a variable?"),
            Message(role="assistant", content="A variable is...")
        ]
        
        prompt = tutor_service.build_prompt(space, messages)
        
        assert "What is a variable?" in prompt

class TestGenerateResponse:
    """Tests for tutor response generation."""
    
    @pytest.mark.asyncio
    async def test_returns_assistant_message(self, tutor_service):
        # Arrange
        space = Space(topic="Python", goal="Learn")
        user_message = "Hello"
        
        # Act
        response = await tutor_service.generate_response(space, user_message)
        
        # Assert
        assert response.role == "assistant"
        assert len(response.content) > 0
    
    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self, tutor_service, mocker):
        # Arrange
        mocker.patch.object(
            tutor_service.client.messages, 
            'create',
            side_effect=anthropic.APIError("Service unavailable")
        )
        
        # Act & Assert
        with pytest.raises(TutorServiceError):
            await tutor_service.generate_response(space, "Hello")
```

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/services/test_tutor.py

# Run specific test
pytest tests/services/test_tutor.py::TestBuildPrompt::test_includes_topic_and_goal

# Run tests matching pattern
pytest -k "test_build"

# Verbose output
pytest -v
```

#### Test Fixtures (conftest.py)

```python
# tests/conftest.py

import pytest
from httpx import AsyncClient
from src.main import app
from src.db.supabase import get_supabase_client

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def client():
    """Async test client for API tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_supabase(mocker):
    """Mock Supabase client for unit tests."""
    return mocker.patch("src.db.supabase.get_supabase_client")

@pytest.fixture
def sample_space():
    """Sample space for testing."""
    return Space(
        id=uuid4(),
        user_id=uuid4(),
        name="Test Space",
        topic="Python",
        goal="Learn basics"
    )

@pytest.fixture
def sample_messages():
    """Sample conversation for testing."""
    return [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi! What would you like to learn?"),
    ]
```

### Frontend (TypeScript/Next.js)

#### File Structure

```
apps/web/
├── app/
│   └── spaces/[id]/chat/
│       └── page.tsx
├── components/
│   └── chat/
│       ├── chat-input.tsx
│       └── chat-input.test.tsx    # Co-located tests
├── lib/
│   ├── api.ts
│   └── api.test.ts
└── jest.config.js
```

#### Writing Tests

```typescript
// components/chat/chat-input.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from './chat-input';

describe('ChatInput', () => {
  it('calls onSend with message when submitted', () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);
    
    const input = screen.getByRole('textbox');
    const button = screen.getByRole('button', { name: /send/i });
    
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(button);
    
    expect(onSend).toHaveBeenCalledWith('Hello');
  });
  
  it('clears input after sending', () => {
    render(<ChatInput onSend={jest.fn()} />);
    
    const input = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));
    
    expect(input.value).toBe('');
  });
  
  it('disables input when disabled prop is true', () => {
    render(<ChatInput onSend={jest.fn()} disabled />);
    
    expect(screen.getByRole('textbox')).toBeDisabled();
    expect(screen.getByRole('button')).toBeDisabled();
  });
  
  it('does not send empty messages', () => {
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);
    
    fireEvent.click(screen.getByRole('button', { name: /send/i }));
    
    expect(onSend).not.toHaveBeenCalled();
  });
});
```

#### Running Tests

```bash
# Run all tests
npm test

# Run in watch mode
npm test -- --watch

# Run specific file
npm test -- chat-input.test.tsx

# Run with coverage
npm test -- --coverage
```

---

## Code Review Checklist

Before merging any code (AI-generated or not):

### Correctness
- [ ] Tests pass
- [ ] Types check (`mypy` / TypeScript)
- [ ] Linting passes
- [ ] Manual testing done for UI changes

### Security
- [ ] No hardcoded secrets
- [ ] Input validation present
- [ ] Auth checks in place for protected routes
- [ ] No SQL injection (use parameterized queries)

### Quality
- [ ] Functions are small (<30 lines)
- [ ] Names are clear and descriptive
- [ ] No dead code
- [ ] No TODOs without issue links
- [ ] Error handling is appropriate

### Architecture
- [ ] Follows existing patterns
- [ ] No circular dependencies
- [ ] Changes are in the right layer (route vs service vs model)

---

## Patterns for This Project

### API Route Pattern

```python
# src/routes/messages.py

from fastapi import APIRouter, Depends, HTTPException
from src.models.schemas import SendMessageRequest, MessageResponse
from src.services.tutor import TutorService
from src.auth import get_current_user

router = APIRouter(prefix="/conversations/{conversation_id}/messages")

@router.post("", response_model=MessageResponse)
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    user: User = Depends(get_current_user),
    tutor: TutorService = Depends(get_tutor_service)
):
    # 1. Validate ownership
    conversation = await get_conversation_or_404(conversation_id, user.id)
    
    # 2. Store user message
    user_message = await store_message(conversation_id, "user", body.content)
    
    # 3. Generate tutor response
    response = await tutor.generate_response(
        space=conversation.space,
        messages=await get_recent_messages(conversation_id)
    )
    
    # 4. Store and return assistant message
    assistant_message = await store_message(conversation_id, "assistant", response)
    return assistant_message
```

### Service Pattern

```python
# src/services/tutor.py

class TutorService:
    def __init__(self, client: Anthropic = None):
        self.client = client or Anthropic()
    
    def build_prompt(self, space: Space, messages: list[Message]) -> str:
        """Build the tutor prompt with context."""
        # Pure function, easy to test
        return f"{SYSTEM_PROMPT}\n\n<context>...</context>"
    
    async def generate_response(self, space: Space, messages: list[Message]) -> str:
        """Generate a tutor response."""
        prompt = self.build_prompt(space, messages)
        
        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=prompt,
                messages=[{"role": m.role, "content": m.content} for m in messages]
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise TutorServiceError("Failed to generate response")
```

### React Component Pattern

```typescript
// components/chat/message-bubble.tsx

interface MessageBubbleProps {
  message: Message;
  isUser: boolean;
}

export function MessageBubble({ message, isUser }: MessageBubbleProps) {
  return (
    <div className={cn(
      "rounded-lg p-3 max-w-[80%]",
      isUser ? "bg-primary text-primary-foreground ml-auto" : "bg-muted"
    )}>
      {message.metadata?.type === 'quiz' ? (
        <QuizBlock quiz={message.metadata} />
      ) : (
        <p className="whitespace-pre-wrap">{message.content}</p>
      )}
    </div>
  );
}
```

---

## Common Mistakes to Avoid

### 1. Testing Implementation, Not Behavior

```python
# ❌ Bad: Tests implementation details
def test_calls_anthropic_client():
    service.generate_response(space, messages)
    mock_client.messages.create.assert_called_once()

# ✅ Good: Tests behavior
def test_returns_response_content():
    response = service.generate_response(space, messages)
    assert isinstance(response, str)
    assert len(response) > 0
```

### 2. Not Isolating Tests

```python
# ❌ Bad: Tests depend on database state
def test_get_messages():
    # Assumes messages exist from previous test
    messages = get_messages(conversation_id)
    assert len(messages) == 5

# ✅ Good: Each test sets up its own state
def test_get_messages(db_session):
    conversation = create_conversation(db_session)
    create_message(db_session, conversation.id, "Hello")
    create_message(db_session, conversation.id, "Hi")
    
    messages = get_messages(conversation.id)
    
    assert len(messages) == 2
```

### 3. Large Commits

```bash
# ❌ Bad: Giant commit
git commit -m "Add chat feature"
# 47 files changed, 2000 insertions

# ✅ Good: Atomic commits
git commit -m "Add Message model"
git commit -m "Add message storage service"
git commit -m "Add POST /messages endpoint"
git commit -m "Add chat input component"
git commit -m "Wire up chat page"
```

### 4. Skipping Type Hints

```python
# ❌ Bad: No types
def process_message(msg, ctx):
    return ctx.get("tutor").respond(msg)

# ✅ Good: Fully typed
async def process_message(
    message: Message, 
    context: ConversationContext
) -> TutorResponse:
    return await context.tutor.respond(message)
```

---

## CI/CD Requirements

Every PR must pass:

```yaml
# .github/workflows/api.yml
- pytest with >80% coverage
- ruff check (linting)
- ruff format --check (formatting)
- mypy (type checking)

# .github/workflows/web.yml
- npm test with >80% coverage
- npm run lint
- npm run build (type checking via tsc)
```

PRs cannot merge until all checks pass.

---

## Quick Reference

### Start a New Feature

```bash
# 1. Create branch
git checkout -b feature/add-quiz-evaluation

# 2. Write test first
# tests/services/test_quiz.py

# 3. Run test (should fail)
pytest tests/services/test_quiz.py

# 4. Implement
# src/services/quiz.py

# 5. Run test (should pass)
pytest tests/services/test_quiz.py

# 6. Run all tests
pytest

# 7. Lint and format
ruff check . && ruff format .

# 8. Commit
git add .
git commit -m "Add quiz evaluation service"

# 9. Push and create PR
git push -u origin feature/add-quiz-evaluation
```

### Debug a Failing Test

```bash
# Run with verbose output
pytest -v tests/services/test_tutor.py

# Run with print statements visible
pytest -s tests/services/test_tutor.py

# Drop into debugger on failure
pytest --pdb tests/services/test_tutor.py

# Run only failing tests from last run
pytest --lf
```

### Check Coverage Gaps

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html
```