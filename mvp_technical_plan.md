# Blossom.ai MVP Technical Plan

## Executive Summary

Blossom.ai is an AI-powered learning platform where users explore topics through conversation with an adaptive AI tutor. The tutor teaches, probes understanding, adapts explanations, and uses quizzes as checkpoints to validate learning. A knowledge map tracks progress in the background, but the primary experience is dialogue.

**Core thesis:** AI should make you smarter, not do your thinking for you.

**Core interaction:** Chat with a tutor that guides exploration, adapts to how you learn, and keeps you honest about whether you actually understand.

---

## What This Is

**Not this:** Quiz app with a knowledge map UI

**This:** AI tutor you chat with to learn things. The tutor:
- Teaches and explains
- Asks probing questions ("can you explain that back?")
- Challenges assumptions ("what would happen if...?")
- Gives examples and analogies
- Adapts when something doesn't land
- Uses quizzes to check understanding
- Steers you toward gaps without being annoying about it

The knowledge map exists, but it's the backbone—not the interface. It tracks what's been covered, what's validated, what approaches worked.

---

## The Feedback Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Explore   │───>│   Validate  │───>│   Adapt     │         │
│  │   (chat)    │    │   (quiz)    │    │  (reteach)  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                  │                  │                 │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              KNOWLEDGE MAP + MASTERY STATE               │   │
│  │  - Topics covered in conversation                        │   │
│  │  - Topics validated via quiz                             │   │
│  │  - Gaps identified                                       │   │
│  │  - Teaching approaches tried + effectiveness             │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         │ informs next move                                     │
│         ▼                                                       │
│  ┌─────────────┐                                               │
│  │  Continue   │───> back to Explore                           │
│  └─────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Explore:** User and tutor converse. User asks questions, tutor explains, tutor asks probing questions, user demonstrates understanding (or doesn't).

**Validate:** When tutor thinks user is ready (or user asks), quiz on recent topics. AI grades responses, identifies what's solid vs shaky.

**Adapt:** If gaps found, tutor reteaches—different angle, more detail, different analogy, worked examples, whatever might work better. Track what approach was used.

**Repeat:** Until mastery is validated.

---

## Two Modes (Start with Guided)

| Mode | AI Behavior | When to Use |
|------|-------------|-------------|
| **Guided** | AI has a plan, steers toward important concepts, checks understanding regularly, doesn't let user skip ahead without demonstrating mastery | Default for new topics, users who want structure |
| **Freeform** | AI responds to user questions, tracks coverage silently, only intervenes if user is stuck or has major gaps | Users who learn by wandering, revisiting familiar topics |

**MVP:** Build guided mode. The chat interface is the same—mode affects AI behavior via system prompt and context injection.

**Signals that shift behavior:**
- New topic, no data → guided
- User asks specific question → answer it, then optionally steer
- Known gaps → guided toward them
- Progressing well → lighter touch
- Stuck or going in circles → intervene

---

## What the Knowledge Map Tracks

The knowledge map is not the UI. It's the data structure that makes the tutor smart.

```
For each topic:
├── covered_in_conversation: bool
├── coverage_depth: shallow | moderate | deep
├── validated_via_quiz: bool
├── mastery_level: 0-100
├── confidence: 0-1 (how sure are we about mastery)
├── misconceptions_identified: []
├── teaching_approaches_tried: [
│     { approach: "analogy_to_cooking", effective: true },
│     { approach: "formal_definition", effective: false }
│   ]
└── last_touched: timestamp
```

**This lets the tutor:**
- Know what's been covered vs. what hasn't
- Not repeat explanations that worked
- Try different approaches when something didn't work
- Prioritize gaps
- Know when to quiz

---

## Conversation Analysis

After each user message (or periodically), analyze the conversation to update state:

**Extract:**
- Topics touched in this exchange
- Whether user demonstrated understanding
- Misconceptions revealed
- Questions that indicate confusion
- Teaching approaches used by tutor

**Update:**
- Coverage map
- Mastery estimates (conversation signals, not just quizzes)
- Approaches tried

**This is background processing.** User doesn't see it. Tutor uses it.

---

## MVP User Journey

```
1. User creates space
   "I want to understand how neural networks work"
   
2. AI generates knowledge map (background)
   Topics, dependencies, sequence
   User doesn't see this directly
   
3. Tutor initiates conversation (guided mode)
   "Let's start with the basic building block—what do you know about 
    how a single neuron works, if anything?"
   
4. Conversation unfolds
   - User responds
   - Tutor teaches, asks probing questions
   - Tutor adapts based on responses
   - Coverage tracked in background
   
5. Tutor initiates quiz checkpoint
   "Before we move on, let me check if this is solid. 
    Quick quiz—3 questions."
   
6. Quiz delivered in chat
   MCQ or short response, inline
   
7. AI evaluates responses
   Updates mastery, identifies gaps
   
8. Tutor responds to results
   - All correct: "Great, let's move on to [next topic]"
   - Gaps found: "Looks like [concept] isn't quite solid. 
     Let me try explaining it differently..."
   
9. Reteach if needed
   Different approach, more examples, etc.
   Track what approach was used
   
10. Continue until user ends session or topic is covered

11. User returns later
    Tutor picks up where they left off, aware of prior progress
```

---

## Tech Stack (Unchanged)

- **Frontend:** Next.js + shadcn/ui + Tailwind (Vercel)
- **Backend:** FastAPI (Cloud Run)
- **Database/Auth/Storage:** Supabase
- **AI:** Claude (Sonnet for tutoring, Haiku for quiz evaluation)
- **Background Jobs:** Cloud Tasks → Cloud Run

---

## Data Model Changes

### New: Conversation Storage

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    summary TEXT,  -- AI-generated summary for context
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb  -- topics touched, teaching approach used, etc.
);
```

### New: Topic Coverage (Conversation-Based)

```sql
CREATE TABLE topic_coverage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id),
    coverage_depth TEXT CHECK (coverage_depth IN ('mentioned', 'explained', 'demonstrated')),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, topic_id, conversation_id)
);
```

### New: Teaching Approaches

```sql
CREATE TABLE teaching_approaches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    approach_type TEXT NOT NULL,  -- 'analogy', 'formal_definition', 'worked_example', etc.
    approach_detail TEXT,          -- specifics: "compared to cooking"
    effective BOOLEAN,             -- did it seem to work?
    conversation_id UUID REFERENCES conversations(id),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Modified: Topic Mastery

```sql
CREATE TABLE topic_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    
    -- Quiz-based signals
    quiz_mastery INT DEFAULT 0 CHECK (quiz_mastery BETWEEN 0 AND 100),
    quiz_confidence NUMERIC(3,2) DEFAULT 0,
    
    -- Conversation-based signals
    conversation_mastery INT DEFAULT 0 CHECK (conversation_mastery BETWEEN 0 AND 100),
    conversation_confidence NUMERIC(3,2) DEFAULT 0,
    
    -- Combined estimate
    mastery_level INT GENERATED ALWAYS AS (
        CASE 
            WHEN quiz_confidence > 0.5 THEN quiz_mastery
            WHEN conversation_confidence > 0.3 THEN conversation_mastery
            ELSE GREATEST(quiz_mastery, conversation_mastery)
        END
    ) STORED,
    
    last_assessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, topic_id)
);
```

### New: User Learning Preferences (Future, but Schema Now)

```sql
CREATE TABLE user_learning_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    
    -- Aggregate preferences learned over time
    preferred_approaches JSONB DEFAULT '[]'::jsonb,  
    -- e.g., [{"type": "analogy", "effectiveness": 0.8}, {"type": "formal", "effectiveness": 0.4}]
    
    pace_preference TEXT CHECK (pace_preference IN ('slow', 'moderate', 'fast')),
    detail_preference TEXT CHECK (detail_preference IN ('high_level', 'moderate', 'detailed')),
    example_preference TEXT CHECK (example_preference IN ('examples_first', 'theory_first', 'mixed')),
    
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

---

## AI Pipeline Changes

### Tutor System Prompt (Guided Mode)

```python
TUTOR_SYSTEM_PROMPT = """
You are an AI tutor helping someone learn {topic}. Your goal is to help them 
genuinely understand, not just memorize or get answers.

<learning_context>
Topic: {topic}
Goal: {goal}
Mode: Guided

Knowledge map:
{knowledge_map_summary}

Current mastery state:
{mastery_summary}

Topics covered this session: {topics_covered_this_session}
Known gaps: {known_gaps}
Teaching approaches that worked for this user: {effective_approaches}
Teaching approaches that didn't work: {ineffective_approaches}
</learning_context>

<tutor_behavior>
1. GUIDE, DON'T LECTURE
   - Ask questions to probe understanding
   - Have them explain things back
   - Don't just give answers—make them think

2. ADAPT
   - If an explanation doesn't land, try a different approach
   - Use analogies, examples, visualizations as needed
   - Match their level—don't talk down, don't overwhelm

3. KEEP THEM HONEST
   - Don't let them nod along without demonstrating understanding
   - Ask "what would happen if...?" and "why does that work?"
   - Call out when something seems shaky

4. TRACK PROGRESS
   - Mentally note what's been covered
   - Know when to quiz: after explaining 2-3 connected concepts
   - Don't move on until foundations are solid

5. QUIZ CHECKPOINTS
   - When ready, say "Let me check if this is solid" and ask 2-4 questions
   - Questions should test understanding, not recall
   - Based on results, either continue or reteach differently

6. STAY FOCUSED
   - If they wander too far, gently steer back
   - Tangents are fine if related; redirect if not
   - Always know what the learning goal is
</tutor_behavior>

<what_not_to_do>
- Don't lecture for multiple paragraphs without engagement
- Don't accept "I understand" without demonstration
- Don't repeat the same explanation if it didn't work
- Don't skip foundations to get to "interesting" stuff
- Don't be condescending or overly cheerful
</what_not_to_do>

Begin by understanding where they are and guiding them from there.
"""
```

### Conversation Analysis Prompt

```python
CONVERSATION_ANALYSIS_PROMPT = """
Analyze this conversation segment to extract learning signals.

<conversation>
{recent_messages}
</conversation>

<knowledge_map>
{knowledge_map_json}
</knowledge_map>

Extract:

1. **topics_touched**: Which topics from the knowledge map were discussed?
   For each: {topic_id, depth: mentioned|explained|demonstrated}

2. **understanding_signals**: Evidence of user understanding or confusion
   - correct_explanations: User accurately explained something
   - misconceptions: User revealed incorrect understanding
   - confusion_indicators: Questions or statements showing confusion

3. **teaching_approaches_used**: How did the tutor explain things?
   For each: {approach_type, detail, seemed_effective: bool}

4. **mastery_updates**: Suggested updates to mastery estimates
   For each topic: {topic_id, delta: -20 to +20, reason}

5. **recommended_next**: What should the tutor do next?
   - continue_topic: Keep going with current topic
   - quiz_checkpoint: Time to validate
   - pivot_approach: Try different teaching method
   - move_on: Ready for next topic
   - address_gap: Need to fix misunderstanding first

Return JSON only.
"""
```

### Quiz-in-Chat Generation

```python
INLINE_QUIZ_PROMPT = """
Generate a quick checkpoint quiz to validate understanding.

<context>
Topics to test: {topics_to_test}
User's current level: {mastery_levels}
Recent conversation topics: {recent_topics}
</context>

Generate {num_questions} questions that:
1. Test understanding, not recall
2. Are appropriate for chat (concise, can be answered in 1-2 sentences or MCQ)
3. Would reveal if they actually understand vs. just nodding along
4. Build on what was just discussed

Format for chat delivery:
- Brief intro: "Quick check on what we covered..."
- Questions numbered, clear
- For MCQ: options on separate lines
- Keep it conversational, not formal exam style

Return JSON:
{
  "intro": "Let's see if this is solid...",
  "questions": [
    {
      "text": "...",
      "type": "mcq" | "short_response",
      "options": ["A. ...", "B. ...", "C. ...", "D. ..."],  // if MCQ
      "correct_answer": "...",
      "tests_topic_id": "...",
      "what_it_reveals": "..."
    }
  ]
}
"""
```

### Quiz Response Evaluation

```python
QUIZ_EVALUATION_PROMPT = """
Evaluate quiz responses and determine next steps.

<quiz>
{quiz_json}
</quiz>

<responses>
{user_responses}
</responses>

For each question:
1. Is the response correct/partially correct/incorrect?
2. What does this reveal about understanding?
3. If wrong, what's the likely misconception?

Then recommend:
- If all solid: what to move on to
- If gaps: how to reteach (different approach than what was tried)

Return JSON:
{
  "evaluations": [
    {
      "question_id": "...",
      "correct": true | false | "partial",
      "understanding_revealed": "...",
      "misconception": "..." // if applicable
    }
  ],
  "overall": "solid" | "shaky" | "needs_reteach",
  "recommendation": {
    "action": "continue" | "reteach" | "practice_more",
    "topics_to_address": ["..."],
    "suggested_approach": "...",  // if reteach
    "next_topic": "..."  // if continue
  },
  "tutor_response": "What the tutor should say next"
}
"""
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  FRONTEND                                    │
│                           (Vercel / Next.js 14)                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CHAT INTERFACE                               │   │
│  │  - Message history                                                   │   │
│  │  - Inline quiz rendering                                            │   │
│  │  - Progress indicators (subtle)                                     │   │
│  │  - "Quiz me" / "Explain more" quick actions                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐     │
│  │  Space List     │  │  Progress View  │  │  Settings               │     │
│  │                 │  │  (optional)     │  │  (mode, preferences)    │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Messages + Quiz responses
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   BACKEND                                    │
│                            (Cloud Run / FastAPI)                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      CONVERSATION ORCHESTRATOR                       │   │
│  │                                                                      │   │
│  │  1. Receive user message                                            │   │
│  │  2. Load context (space, knowledge map, mastery, history)           │   │
│  │  3. Inject context into tutor prompt                                │   │
│  │  4. Get tutor response (Claude)                                     │   │
│  │  5. If quiz: render quiz, await responses, evaluate                 │   │
│  │  6. Analyze conversation (background)                               │   │
│  │  7. Update state (coverage, mastery, approaches)                    │   │
│  │  8. Return response                                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │  Knowledge  │  │   Mastery   │  │    Quiz     │  │  Conversation   │   │
│  │   Service   │  │   Tracker   │  │   Service   │  │    Analyzer     │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI LAYER (Claude)                              │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐     │
│  │  Tutor          │  │  Conversation   │  │  Quiz Generation        │     │
│  │  (Sonnet)       │  │  Analyzer       │  │  + Evaluation           │     │
│  │                 │  │  (Haiku)        │  │  (Sonnet/Haiku)         │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SUPABASE                                        │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐     │
│  │  spaces   │ │  topics   │ │ messages  │ │ mastery   │ │ teaching  │     │
│  │           │ │           │ │           │ │           │ │ approaches│     │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Conversation Flow Detail

```
User sends message
        │
        ▼
┌───────────────────┐
│  Load context     │
│  - Space + topic  │
│  - Knowledge map  │
│  - Mastery state  │
│  - Last N messages│
│  - Teaching prefs │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Build tutor      │
│  prompt with      │
│  context          │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Claude (Sonnet)  │
│  generates        │
│  response         │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐     Yes    ┌───────────────────┐
│  Is this a quiz   │───────────>│  Render quiz in   │
│  checkpoint?      │            │  chat, await      │
└─────────┬─────────┘            │  responses        │
          │ No                   └─────────┬─────────┘
          │                                │
          │                                ▼
          │                      ┌───────────────────┐
          │                      │  Evaluate quiz    │
          │                      │  (Claude)         │
          │                      └─────────┬─────────┘
          │                                │
          │                                ▼
          │                      ┌───────────────────┐
          │                      │  Generate tutor   │
          │                      │  response to      │
          │                      │  results          │
          │                      └─────────┬─────────┘
          │                                │
          ▼                                ▼
┌───────────────────────────────────────────────────┐
│               Return response to user              │
└───────────────────────┬───────────────────────────┘
                        │
                        ▼ (async, don't block)
┌───────────────────────────────────────────────────┐
│            Analyze conversation                    │
│  - Topics covered                                  │
│  - Understanding signals                           │
│  - Update mastery estimates                        │
│  - Log teaching approaches                         │
└───────────────────────────────────────────────────┘
```

---

## What to Build for MVP

| Feature | Include? | Notes |
|---------|----------|-------|
| Space creation (topic + goal) | ✅ | Entry point |
| Knowledge map generation | ✅ | Background, user doesn't see |
| Chat interface | ✅ | **Primary UI** |
| Guided tutor mode | ✅ | Start here |
| Inline quizzes | ✅ | Part of chat flow |
| Quiz evaluation | ✅ | Drives feedback loop |
| Conversation analysis | ✅ | Background, updates state |
| Mastery tracking | ✅ | Combined conversation + quiz signals |
| Teaching approach logging | ✅ | Schema + basic logging |
| Progress view | ⚠️ Minimal | Simple "topics covered" list |
| Freeform mode | ❌ Defer | Add after guided works |
| Learning profile adaptation | ❌ Defer | Track data now, use later |
| Document uploads | ❌ Defer | Not core to chat-first |

---

## What to Defer

| Feature | Why Defer |
|---------|-----------|
| Freeform mode | Get guided right first |
| Learning style adaptation | Need data first; track now, adapt later |
| Document uploads | Chat-first; can enrich map later |
| Knowledge map visualization | Not the UI; maybe never needed |
| Progress dashboard | Minimal for MVP; chat shows progress |
| Multiple spaces active | One at a time is fine |
| Voice/audio | Text first |
| Mobile app | PWA/responsive is enough |

---

## Cost Estimation

### Per-User Cost Model (Chat-First)

```
Assumptions:
- 10 conversation sessions/month
- ~20 messages per session = 200 messages/month
- 1 knowledge map generation
- 3 quiz checkpoints per session = 30 quizzes/month
- Background analysis on every exchange

┌────────────────────────┬──────────┬────────────┬──────────┬─────────────┐
│ Operation              │ Model    │ Tokens/op  │ Ops/mo   │ Cost/mo     │
├────────────────────────┼──────────┼────────────┼──────────┼─────────────┤
│ Knowledge map gen      │ Sonnet   │ ~6K out    │ 1        │ $0.27       │
│ Tutor responses        │ Sonnet   │ ~800 out   │ 200      │ $7.20       │
│ Conversation analysis  │ Haiku    │ ~500 out   │ 200      │ $0.25       │
│ Quiz generation        │ Sonnet   │ ~1K out    │ 30       │ $1.35       │
│ Quiz evaluation        │ Haiku    │ ~400 out   │ 30       │ $0.03       │
├────────────────────────┼──────────┼────────────┼──────────┼─────────────┤
│ TOTAL                  │          │            │          │ ~$9/user    │
└────────────────────────┴──────────┴────────────┴──────────┴─────────────┘
```

**Higher than quiz-only approach** because conversation is more expensive than MCQs. But it's the actual product.

**Ways to reduce:**
- Cache knowledge maps (reuse across users for common topics)
- Batch conversation analysis (every 5 messages, not every 1)
- Shorter context windows (summarize history)
- Haiku for simpler tutor exchanges (detecting when depth isn't needed)

---

## First 30 Days Roadmap

```
Week 1: Foundation
├── Supabase setup (auth, db, storage)
├── Next.js + shadcn/ui
├── Basic auth flow
├── Deploy to Vercel + Cloud Run
├── Schema: users, spaces, conversations, messages
└── Simple chat UI (no AI yet, just stores messages)

Week 2: Knowledge Map + Basic Tutor
├── Space creation: topic + goal
├── Knowledge map generation (Claude)
├── Schema: knowledge_maps, topics, topic_dependencies
├── Tutor system prompt (guided mode)
├── Basic conversation loop: user → tutor → user
└── Context injection: space + knowledge map into prompt

Week 3: Quizzes + Mastery
├── Inline quiz generation
├── Quiz UI in chat
├── Quiz evaluation
├── Mastery tracking from quiz results
├── Tutor responds to quiz results (continue/reteach)
└── Schema: quizzes, quiz_questions, quiz_responses, topic_mastery

Week 4: Conversation Analysis + Polish
├── Background conversation analysis
├── Update mastery from conversation signals
├── Teaching approach logging
├── Basic progress indicator in UI
├── Dogfood with yourself
├── Bug fixes, prompt tuning
└── Invite 2-3 friends to test
```

---

## Success Metrics

| Metric | What It Tells You |
|--------|-------------------|
| Session length | Are they engaged? |
| Return rate (7 days) | Is it valuable? |
| Quiz performance over time | Are they learning? |
| Topics covered per session | Is progress happening? |
| Reteach frequency | Is the tutor effective? |
| User feedback (thumbs) | Do they feel it helps? |

**The core question:**
> Do users who use Blossom understand things better than they would have otherwise?

Proxies: they come back, quiz scores improve, they cover topics, they say it helped.

---

## Summary

**What changed from v3:**

| v3 (Quiz-First) | v4 (Chat-First) |
|-----------------|-----------------|
| Quiz flows are the UI | Chat is the UI |
| Knowledge map is visible | Knowledge map is backend |
| Quizzes drive learning | Conversation drives learning |
| Quizzes validate | Quizzes are checkpoints |
| Static question sets | Adaptive tutor behavior |
| ~$1.50/user/month | ~$9/user/month |

**What stayed:**
- Tech stack
- Knowledge map as backbone
- Mastery tracking
- Assessment events architecture
- Gap identification concept

**The bet:**
Chat-first is a better learning experience. It's more expensive but more valuable. If it works, users will pay for it.