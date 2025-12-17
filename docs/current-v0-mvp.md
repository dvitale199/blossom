# Blossom.ai v0 — MVP README

## Implementation Status

### Phase 1: Foundation
- [ ] Environment setup complete (see below)
- [ ] Run `blossom-schema.sql` in Supabase
- [ ] FastAPI project skeleton with health check
- [ ] Basic /chat endpoint (stores messages, no AI)
- [ ] Supabase auth integration
- [ ] Frontend: auth flow, basic chat UI

### Phase 2: Tutor
- [ ] Claude API integration
- [ ] Prompt assembly (load profile → inject context)
- [ ] Conversation persistence
- [ ] Session start/end events

### Phase 3: Background Job
- [ ] Extraction prompt integration
- [ ] Session timeout detection (30 min)
- [ ] Profile update logic
- [ ] Quiz attempt logging

### Phase 4: Polish
- [ ] Event emission (all event types)
- [ ] Error handling
- [ ] Basic settings page
- [ ] Mobile responsive

---

## Environment Setup

- [ ] Supabase project created
- [ ] `blossom-schema.sql` executed
- [ ] Environment variables set (see below)
- [ ] FastAPI running locally
- [ ] Next.js running locally

### Required Environment Variables

```bash
# Backend (apps/api/.env)
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# Frontend (apps/web/.env.local)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional (for testing other providers)
OPENAI_API_KEY=
GOOGLE_API_KEY=
```

---

## Files Reference

| Document | Purpose |
|----------|---------|
| `blossom-ai-architecture.md` | Prompts, schemas, extraction logic, code patterns |
| `blossom-schema.sql` | Database setup — run once in Supabase |
| `blossom-CLAUDE.md` | Quick reference for AI assistants |

---

## What We're Testing

**Hypothesis:** An AI tutor that teaches through conversation, asks probing questions, and validates understanding via quizzes helps people learn better than just asking ChatGPT.

**v0 tests this with the smallest possible build.**

---

## v0 Scope

### What We're Building

1. **Chat with an AI tutor** that behaves like a tutor, not an answer machine
2. **Inline quizzes** as checkpoints to validate understanding
3. **Conversation persistence** so users can continue where they left off

### What We're NOT Building (Yet)

| Deferred | Why | When |
|----------|-----|------|
| Knowledge map generation | Tutor can improvise; test if chat works first | v1 |
| Mastery calculations | Store data now, calculate later | v1 |
| Conversation analysis | Store messages, analyze later | v1 |
| Teaching approach tracking | Not needed until we prove core works | v1 |
| Gap identification | Let tutor intuit from conversation | v1 |
| Progress UI | Users can feel progress; don't need dashboard | v1 |
| Guided vs freeform modes | Start with one behavior, refine | v1 |
| Learning profiles | Need data first | v2 |

---

## Architecture Decisions (Future-Proof)

These choices allow v1+ features without rewrites:

### 1. Spaces as the Container

```
Space = a learning context (topic + goal)
├── Has many conversations
├── Will have: knowledge map, mastery state, gaps
└── For now: just holds conversations
```

**Why:** When we add knowledge maps and mastery tracking, they attach to spaces. No schema changes needed.

### 2. Conversations and Messages Stored Separately

```
Conversation = a session (one chat thread)
├── Has many messages
├── Will have: summary, topics_covered, analysis
└── For now: just a container for messages

Message = a single exchange
├── role: user | assistant
├── content: the text
├── Will have: metadata (topics touched, quiz results, etc.)
└── For now: just role + content + timestamp
```

**Why:** When we add conversation analysis, we annotate messages with metadata. Structure is already there.

### 3. Quizzes are Messages with Structure

Quizzes appear inline in chat. We store them as messages with `type: quiz` and structured metadata.

```
Message (quiz):
├── role: assistant
├── content: rendered quiz text
├── metadata: { type: "quiz", questions: [...], responses: [...], evaluated: bool }
```

**Why:** Quizzes are part of the conversation flow, not a separate system. When we add mastery tracking, we extract quiz results from message metadata.

### 4. JSONB Metadata Fields Everywhere

Every table has a `metadata JSONB` column. Use it for:
- Stuff we're not sure about yet
- Future features we want to track data for
- Per-record flags and annotations

**Why:** Avoids schema changes during rapid iteration. Migrate to proper columns once patterns stabilize.

### 5. Tutor Behavior via System Prompt + Context Injection

The tutor is Claude with:
- A system prompt defining behavior
- Context injected per-request (space info, recent messages, quiz history)

```python
def build_tutor_prompt(space, messages, quiz_history):
    return f"""
    {TUTOR_SYSTEM_PROMPT}
    
    <context>
    Topic: {space.topic}
    Goal: {space.goal}
    Recent conversation: {format_messages(messages[-20:])}
    Quiz history: {format_quiz_summary(quiz_history)}
    </context>
    """
```

**Why:** When we add knowledge maps and mastery state, we inject more context. The pattern doesn't change—just the context payload.

### 6. Backend Orchestrates, Frontend Renders

Frontend is dumb:
- Sends messages
- Renders responses
- Renders quizzes when message type is quiz
- Sends quiz answers

Backend is smart:
- Manages conversation state
- Decides what context to inject
- Calls Claude
- Handles quiz flow

**Why:** Intelligence lives in one place. Easier to iterate on tutor behavior without frontend changes.

---

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Frontend | Next.js 14 + shadcn/ui + Tailwind | Vercel deployment |
| Backend | FastAPI | Cloud Run deployment |
| Database | Supabase (PostgreSQL) | Auth + DB + Storage |
| Auth | Supabase Auth | Google OAuth + email |
| AI | Claude API (Sonnet) | Single model for v0 |
| Background Jobs | None for v0 | Add Cloud Tasks when needed |

---

## Data Model (v0)

Minimal schema that supports future expansion.

```sql
-- Enums (expandable later)
CREATE TYPE space_context AS ENUM ('exploratory');  -- Add 'professional', 'academic' later
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');

-- Users (Supabase Auth handles this, but we reference it)
-- auth.users exists automatically

-- Spaces: a learning context
CREATE TABLE spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Core fields
    name TEXT NOT NULL,
    topic TEXT NOT NULL,
    goal TEXT,
    
    -- Future-proofing
    context_type space_context NOT NULL DEFAULT 'exploratory',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Expansion slot
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Conversations: a chat session within a space
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT now(),
    last_message_at TIMESTAMPTZ DEFAULT now(),
    
    -- Future: AI-generated summary for context compression
    summary TEXT,
    
    -- Expansion slot
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Messages: individual exchanges
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Core fields
    role message_role NOT NULL,
    content TEXT NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    
    -- Expansion slot: will hold quiz data, topic annotations, etc.
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX idx_spaces_user ON spaces(user_id);
CREATE INDEX idx_conversations_space ON conversations(space_id);
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(conversation_id, created_at);

-- Row Level Security
ALTER TABLE spaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their spaces"
    ON spaces FOR ALL USING (auth.uid() = user_id);

ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own their conversations"
    ON conversations FOR ALL USING (auth.uid() = user_id);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users own messages in their conversations"
    ON messages FOR ALL USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE user_id = auth.uid()
        )
    );
```

### Quiz Data Structure (Stored in message.metadata)

When the tutor generates a quiz, we store it as a message:

```json
{
  "type": "quiz",
  "quiz_id": "uuid",
  "questions": [
    {
      "id": "q1",
      "text": "What would happen if...?",
      "type": "mcq",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
      "correct_answer": "B"
    }
  ],
  "status": "pending" | "completed",
  "responses": [
    {
      "question_id": "q1",
      "user_answer": "B",
      "is_correct": true,
      "feedback": "..."
    }
  ],
  "completed_at": "timestamp"
}
```

**Why in metadata:** Quizzes are part of the message flow. When we add proper quiz tables and mastery tracking, we can migrate this data out. For v0, this keeps it simple.

---

## API Endpoints (v0)

```
POST   /api/spaces                     Create a space
GET    /api/spaces                     List user's spaces
GET    /api/spaces/:id                 Get space details

POST   /api/spaces/:id/conversations   Start a new conversation
GET    /api/spaces/:id/conversations   List conversations in space

GET    /api/conversations/:id          Get conversation with messages
POST   /api/conversations/:id/messages Send a message, get tutor response

POST   /api/messages/:id/quiz-response Submit quiz answers (if message is a quiz)
```

### Key Endpoint: Send Message

```python
@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    body: SendMessageRequest,
    user: User = Depends(get_current_user)
):
    # 1. Verify ownership
    conversation = await get_conversation(conversation_id, user.id)
    space = await get_space(conversation.space_id)
    
    # 2. Store user message
    user_message = await store_message(
        conversation_id=conversation_id,
        role="user",
        content=body.content
    )
    
    # 3. Load context
    recent_messages = await get_recent_messages(conversation_id, limit=20)
    quiz_history = await get_quiz_history(conversation_id)
    
    # 4. Build prompt and call Claude
    tutor_response = await get_tutor_response(
        space=space,
        messages=recent_messages,
        quiz_history=quiz_history
    )
    
    # 5. Check if response includes a quiz
    quiz_data = extract_quiz_if_present(tutor_response)
    
    # 6. Store assistant message
    assistant_message = await store_message(
        conversation_id=conversation_id,
        role="assistant",
        content=tutor_response.content,
        metadata={"type": "quiz", **quiz_data} if quiz_data else {}
    )
    
    # 7. Update conversation timestamp
    await update_conversation_timestamp(conversation_id)
    
    # 8. Return response
    return {
        "message": assistant_message,
        "has_quiz": quiz_data is not None
    }
```

---

## Tutor System Prompt (v0)

This is where the product lives. Everything else is plumbing.

```python
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
```

### Context Injection Template

```python
CONTEXT_TEMPLATE = """
<learning_context>
Topic: {topic}
Goal: {goal}

Recent conversation:
{formatted_messages}

Quiz history this session:
{quiz_summary}
</learning_context>

Continue the tutoring session. Remember where you left off.
"""
```

---

## Frontend Structure (v0)

```
app/
├── (auth)/
│   ├── login/page.tsx
│   └── signup/page.tsx
├── (main)/
│   ├── layout.tsx           # Sidebar + main area
│   ├── page.tsx             # Redirect to /spaces
│   ├── spaces/
│   │   ├── page.tsx         # List spaces
│   │   ├── new/page.tsx     # Create space form
│   │   └── [id]/
│   │       ├── page.tsx     # Space view (redirects to active conversation)
│   │       └── chat/page.tsx # Chat interface
│   └── settings/page.tsx    # User settings (minimal)
├── components/
│   ├── chat/
│   │   ├── chat-container.tsx
│   │   ├── message-list.tsx
│   │   ├── message-bubble.tsx
│   │   ├── chat-input.tsx
│   │   └── quiz-block.tsx   # Renders inline quiz
│   ├── spaces/
│   │   ├── space-card.tsx
│   │   └── create-space-form.tsx
│   └── ui/                  # shadcn components
├── lib/
│   ├── supabase.ts          # Supabase client
│   ├── api.ts               # Backend API calls
│   └── types.ts             # TypeScript types
└── hooks/
    ├── use-chat.ts          # Chat state management
    └── use-spaces.ts        # Space data fetching
```

### Key Component: Quiz Block

```tsx
// components/chat/quiz-block.tsx

interface QuizBlockProps {
  quiz: QuizData;
  onSubmit: (responses: QuizResponse[]) => void;
  disabled?: boolean;
}

export function QuizBlock({ quiz, onSubmit, disabled }: QuizBlockProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  
  const handleSubmit = () => {
    const responses = quiz.questions.map(q => ({
      question_id: q.id,
      user_answer: answers[q.id]
    }));
    onSubmit(responses);
  };
  
  if (quiz.status === 'completed') {
    return <QuizResults quiz={quiz} />;
  }
  
  return (
    <div className="quiz-block border rounded-lg p-4 my-2">
      <p className="font-medium mb-4">Quick check:</p>
      {quiz.questions.map(question => (
        <QuizQuestion
          key={question.id}
          question={question}
          selected={answers[question.id]}
          onSelect={(answer) => setAnswers(a => ({...a, [question.id]: answer}))}
          disabled={disabled}
        />
      ))}
      <Button onClick={handleSubmit} disabled={disabled || Object.keys(answers).length < quiz.questions.length}>
        Check Answers
      </Button>
    </div>
  );
}
```

---

## Build Plan

### Week 1: Foundation

```
Day 1-2: Project Setup
├── Create monorepo structure (apps/web, apps/api)
├── Set up Next.js with shadcn/ui + Tailwind
├── Set up FastAPI with basic structure
├── Set up Supabase project (db + auth)
├── Deploy skeleton to Vercel + Cloud Run
└── CI/CD: GitHub Actions for both

Day 3-4: Auth + Spaces
├── Supabase Auth integration (Google OAuth)
├── Protected routes in Next.js
├── Create space flow (form → API → DB)
├── List spaces page
└── Basic space detail page

Day 5: Database + API Foundation
├── Run schema migrations
├── Implement spaces CRUD endpoints
├── Implement conversations endpoints
├── Test API with curl/Postman
└── Connect frontend to API
```

### Week 2: Chat Core

```
Day 1-2: Chat Interface
├── Chat container component
├── Message list + bubbles
├── Chat input with submit
├── Scroll behavior (auto-scroll, load more)
└── Loading states

Day 3-4: Tutor Integration
├── Implement send_message endpoint
├── Tutor system prompt (first draft)
├── Context injection (space + messages)
├── Claude API integration
├── Stream responses to frontend
└── Store messages in DB

Day 5: Conversation Continuity
├── Load conversation history on page load
├── Resume conversation flow
├── Handle new vs existing conversation
└── Test multi-session learning
```

### Week 3: Quizzes

```
Day 1-2: Quiz Generation
├── Quiz detection in tutor responses
├── Parse quiz XML format
├── Store quiz data in message metadata
├── Quiz block component (render questions)
└── Answer selection UI

Day 3-4: Quiz Evaluation
├── Submit quiz answers endpoint
├── Evaluate answers (correct/incorrect)
├── Generate feedback
├── Update message metadata with results
├── Tutor responds to quiz results
└── Quiz results display

Day 5: Polish Quiz Flow
├── Quiz state management (pending/completed)
├── Disable input while quiz active
├── Smooth transitions
└── Edge cases (partial answers, back navigation)
```

### Week 4: Polish + Dogfood

```
Day 1-2: Tutor Prompt Refinement
├── Test with real topics
├── Tune system prompt based on behavior
├── Improve quiz question quality
├── Better reteaching after wrong answers
└── Balance guided vs responsive

Day 3-4: UX Polish
├── Empty states
├── Error handling
├── Loading skeletons
├── Mobile responsive
├── Basic settings page
└── Conversation list in sidebar

Day 5: Launch Dogfood
├── Deploy stable version
├── Create test accounts for friends
├── Write brief usage guide
├── Set up feedback channel (simple form or Discord)
└── Start using it yourself daily
```

---

## Success Criteria (v0)

After 2 weeks of dogfooding with 3-5 users:

| Signal | Target | How to Measure |
|--------|--------|----------------|
| Return usage | Users come back 3+ times | DB: sessions per user |
| Session depth | 10+ messages per session | DB: messages per conversation |
| Quiz engagement | Users complete quizzes | DB: quiz completion rate |
| Perceived value | "This helps" | Ask them directly |
| Tutor quality | "Feels like a tutor, not ChatGPT" | Ask them directly |

**If these hit:** Move to v1 (knowledge maps, mastery tracking, adaptation)

**If these miss:** Diagnose why before adding complexity
- Is the tutor prompt the problem?
- Is quiz quality the problem?
- Is the core hypothesis wrong?

---

## What v1 Adds (After v0 Validates)

Once we know the core works:

```
v1 Additions:
├── Knowledge map generation
│   └── AI generates topic structure from space topic
├── Mastery tracking
│   └── Calculate mastery from quiz results + conversation signals
├── Conversation analysis (background)
│   └── Extract topics covered, understanding signals
├── Gap identification
│   └── Surface weak areas for targeting
├── Progress visibility
│   └── Simple UI showing topics covered/mastered
└── Teaching approach logging
    └── Track what explanations work for each user
```

The schema already supports this. We're just not building the features yet.

---

## Local Development

```bash
# Clone and setup
git clone <repo>
cd blossom

# Frontend
cd apps/web
npm install
cp .env.example .env.local  # Add Supabase keys
npm run dev

# Backend
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add Supabase + Claude keys
uvicorn src.main:app --reload

# Database
# Run migrations via Supabase dashboard or CLI
```

### Environment Variables

```bash
# apps/web/.env.local
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000

# apps/api/.env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
ANTHROPIC_API_KEY=
```

---

## File Structure

```
blossom/
├── apps/
│   ├── web/                    # Next.js frontend
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   ├── hooks/
│   │   ├── package.json
│   │   └── next.config.js
│   │
│   └── api/                    # FastAPI backend
│       ├── src/
│       │   ├── main.py
│       │   ├── config.py
│       │   ├── routes/
│       │   │   ├── spaces.py
│       │   │   ├── conversations.py
│       │   │   └── messages.py
│       │   ├── services/
│       │   │   ├── tutor.py
│       │   │   └── quiz.py
│       │   ├── models/
│       │   │   └── schemas.py
│       │   └── db/
│       │       └── supabase.py
│       ├── requirements.txt
│       └── Dockerfile
│
├── .github/
│   └── workflows/
│       ├── web.yml
│       └── api.yml
│
├── docs/
│   ├── v0-mvp.md              # This file
│   └── v1-plan.md             # Full plan for reference
│
└── README.md                   # Project overview + setup
```

---

## Summary

**v0 is the smallest thing that tests the core hypothesis.**

Build:
- Chat with a tutor
- Inline quizzes
- Conversation persistence

Defer:
- Knowledge maps
- Mastery tracking
- Analysis pipelines
- Progress UI

Validate:
- Do users come back?
- Do they engage with quizzes?
- Do they feel like they're learning?

Then build v1.