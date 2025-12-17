# Blossom AI Architecture: MVP Decisions

## Overview

This document captures architectural decisions for Blossom's AI tutoring system. The goal: a simple, extensible architecture that validates whether conversational tutoring creates genuine learning outcomes.

### Core Thesis
"AI should make people smarter, not offload their thinking."

### MVP Architecture: Simple First

Instead of a multi-agent system, we're starting with:

| Component | Level | Description |
|-----------|-------|-------------|
| **Tutor** | Level 2 (Stateful + Context) | Real-time chat interface, prompt-driven behavior |
| **Background Job** | Level 0 (Single Prompt) | Async extraction after sessions, updates profile |

Quizzes are embedded in the Tutor's behavior, not a separate agent. We expand architecture only after validating the core learning experience works.

---

## 1. User Profile Schema

### Design Principles
- Free text over rigid taxonomies (goals, topics, observations)
- Denormalize recent context for fast Tutor reads
- Append-only for learning signals, reconcile later
- Separate table for detailed quiz history

### Core Table: `user_profiles`

```sql
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- User-provided
  display_name TEXT,
  learning_goals TEXT,  -- free text
  self_assessed_background TEXT,
  preferences JSONB DEFAULT '{}',  -- {quiz_frequency, session_length, etc.}
  
  -- Learning state
  topics JSONB DEFAULT '{}',  -- see structure below
  
  -- Learning style
  learning_style_observations JSONB DEFAULT '[]',  -- array of strings, append-only
  
  -- Session context
  current_topic TEXT,
  recent_sessions JSONB DEFAULT '[]',  -- last 3 session summaries
  open_questions JSONB DEFAULT '[]',
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_session_at TIMESTAMPTZ
);
```

### Topics JSONB Structure

```json
{
  "u-substitution": {
    "first_seen": "2024-01-15T10:00:00Z",
    "last_seen": "2024-01-18T15:00:00Z",
    "sessions_count": 3,
    "comprehension": 4,
    "quiz_scores": [1.0, 0.8],
    "last_quizzed": "2024-01-18T15:30:00Z",
    "notes": "Understood mechanics, building intuition for when to apply"
  }
}
```

**Comprehension Scale (1-5):**
1. No understanding, completely lost
2. Struggling, needs significant help
3. Learning, getting it but not solid
4. Solid, understands well
5. Mastered, could teach it

*Future feature: Topic tree visualization where users browse topics hierarchically, colored by comprehension (1=red → 5=green).*

### Quiz History Table: `quiz_attempts`

```sql
CREATE TABLE quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  session_id UUID,
  topic TEXT,
  question_text TEXT,
  user_answer TEXT,
  correct BOOLEAN,
  confidence_signals JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Tunable Parameters
- Recent sessions to denormalize: **3** (adjustable based on testing)
- Topics to include in Tutor context: **10 most recent** (by `last_seen`)
- Learning style reconciliation: **none for MVP** (append-only)

---

## 2. Background Job Extraction Schema

### Design Principles
- Single LLM call with structured JSON output
- Extract everything needed to update profile in one pass
- Capture signals now even if not used immediately
- Handle edge cases gracefully (short sessions, off-topic chat)

### Trigger
Runs on `session_ended` event (explicit close or 30 min inactivity timeout).

### Input
- Full conversation transcript
- Current user profile (for context)
- Session metadata (start time, duration, message count)

### Output Schema

```json
{
  "session_summary": {
    "date": "2024-01-18T15:00:00Z",
    "duration_minutes": 25,
    "summary": "2-4 sentences describing what happened",
    "topics": ["integration", "u-substitution"],
    "mood": "engaged"
  },
  
  "topics_discussed": [
    {
      "name": "u-substitution",
      "is_new": true,
      "comprehension": 3,
      "notes": "Understood mechanics but still building intuition"
    }
  ],
  
  "quiz_results": [
    {
      "topic": "u-substitution",
      "question_summary": "Evaluate ∫2x·cos(x²)dx",
      "correct": true,
      "attempts": 1,
      "notes": "Solved confidently after hint about choosing u"
    }
  ],
  
  "learning_style_observations": [
    "Prefers to see multiple worked examples before attempting problems"
  ],
  
  "open_questions": [
    "When do you use substitution vs. integration by parts?"
  ],
  
  "suggested_next_topic": "integration by parts",
  
  "flags": {
    "user_expressed_frustration": false,
    "significant_struggle": false,
    "breakthrough_moment": true,
    "requested_more_practice": true
  }
}
```

### Mood Options
`engaged` | `frustrated` | `confused` | `confident` | `neutral`

### Edge Cases
- **Short/abandoned sessions:** Produce minimal output, note in summary
- **Off-topic conversation:** Empty `topics_discussed`, summary reflects casual chat
- **Quiz-heavy session:** Long `quiz_results` array, summary notes practice focus

### Profile Update Logic

```python
def update_profile_from_extraction(profile, extraction):
    # Append session summary (keep last 3)
    profile.recent_sessions = (
        [extraction.session_summary] + profile.recent_sessions
    )[:3]
    
    # Update topics
    for topic in extraction.topics_discussed:
        if topic.name in profile.topics:
            profile.topics[topic.name].last_seen = now()
            profile.topics[topic.name].sessions_count += 1
            if topic.comprehension:
                profile.topics[topic.name].comprehension = topic.comprehension
        else:
            profile.topics[topic.name] = {
                "first_seen": now(),
                "last_seen": now(),
                "sessions_count": 1,
                "comprehension": topic.comprehension,
                "quiz_scores": []
            }
    
    # Append quiz scores to topics
    for quiz in extraction.quiz_results:
        if quiz.topic in profile.topics:
            profile.topics[quiz.topic].quiz_scores.append(quiz.correct)
            profile.topics[quiz.topic].last_quizzed = now()
    
    # Append learning observations
    profile.learning_style_observations.extend(
        extraction.learning_style_observations
    )
    
    # Update session context
    profile.open_questions = extraction.open_questions
    profile.current_topic = extraction.suggested_next_topic
    profile.last_session_at = now()
    
    return profile
```

---

## 3. Tutor Prompt Structure

### Design Principles
- Layered prompt with clear sections (static philosophy + dynamic context)
- Socratic approach: ask before telling, guide don't lecture
- Quizzes woven naturally + explicit checks at milestones
- No tools for MVP — prompt-driven behavior, Background Job extracts signals
- Neutral persona, no name or distinct personality

### Prompt Assembly

```python
def build_tutor_prompt(user_profile):
    return f"""
{CORE_IDENTITY}

{QUIZ_GUIDELINES}

## About This User

Name: {user_profile.display_name or "there"}

Goals: {user_profile.learning_goals or "Not specified yet"}

Background: {user_profile.self_assessed_background or "Not specified yet"}

Current Topic: {user_profile.current_topic or "None yet"}

Open Questions:
{format_list(user_profile.open_questions) or "None"}

Recent Sessions:
{format_sessions(user_profile.recent_sessions) or "This is your first session"}

Topics Studied (10 most recent):
{format_topics(get_recent_topics(user_profile.topics, 10)) or "None yet"}

Learning Style:
{format_list(user_profile.learning_style_observations) or "Still learning how you learn best"}

{SESSION_CONTINUITY}

{BOUNDARIES}
"""
```

### Section 1: Core Identity (Static)

Store as `CORE_IDENTITY` constant:

```python
CORE_IDENTITY = """
## Who You Are

You are a tutor on Blossom, an AI learning platform. Your goal is to help users genuinely understand topics, not just receive information.

## Teaching Philosophy

- Ask questions before giving answers. Guide users to discover insights themselves.
- Prefer "What do you think would happen if...?" over "Here's what happens..."
- When a user asks a question, first assess what they already understand.
- Give the minimum explanation needed, then check understanding.
- Celebrate genuine understanding, not just correct answers.
- If a user is struggling, break things down smaller rather than explaining more.
- Never make users feel stupid. Confusion is part of learning.

## What You Don't Do

- Don't lecture. Keep explanations concise.
- Don't give answers when you could ask a leading question.
- Don't over-praise. Be warm but genuine.
- Don't assume understanding from a correct answer — probe deeper.
"""
```

### Section 2: Quiz Guidelines (Static)

Store as `QUIZ_GUIDELINES` constant:

```python
QUIZ_GUIDELINES = """
## Checking Understanding

Regularly verify the user actually understands, don't just take their word for it.

### Informal Checks (use frequently)
- "Can you explain that back to me in your own words?"
- "What would happen if we changed X to Y?"
- "Why do you think that's the case?"
- "Can you think of an example where this applies?"

### Formal Quizzes (use at milestones)
Trigger a formal quiz when:
- A topic has been discussed for 10+ messages without assessment
- The user says they understand and wants to move on
- You've covered a natural checkpoint in the material
- The user explicitly asks for a quiz

Format for formal quizzes:
- State clearly: "Let me check your understanding with a quick question."
- Ask ONE question at a time
- Wait for their answer before responding
- If correct: brief acknowledgment, optionally probe deeper
- If incorrect: don't give the answer immediately — ask what led them there, guide them
"""
```

### Section 3: Session Continuity (Static)

Store as `SESSION_CONTINUITY` constant:

```python
SESSION_CONTINUITY = """
## Session Continuity

This is a continuing learning relationship. Reference past sessions naturally:
- "Last time we worked on X — want to continue or try something new?"
- "You mentioned struggling with Y before — has that clicked yet?"
- "I remember you prefer examples first, so let me start there."

If open questions exist from last session, consider addressing them early.

If the user is returning after a break (several days), briefly re-orient:
- "Welcome back! We were exploring X last time."
"""
```

### Section 4: Boundaries (Static)

Store as `BOUNDARIES` constant:

```python
BOUNDARIES = """
## Boundaries

**Off-topic requests:** You can have casual conversation, but gently guide back to learning if it continues. You're a tutor, not a general assistant.

**Requests for answers:** If a user asks you to just give them an answer (e.g., homework), explain that you'll help them understand how to get there, but won't just provide answers.

**Frustration:** If a user is frustrated, acknowledge it. Consider suggesting a break, a different approach, or an easier entry point.

**Beyond your scope:** If asked about something you can't help with, say so clearly and suggest alternatives.
"""
```

### Tools
None for MVP. Add `log_event` or retrieval tools if Background Job extraction proves insufficient.

---

## 4. Event Taxonomy

### Design Principles
- Capture meaningful moments, not raw activity
- Background Job is the primary event emitter
- Events stored in dedicated Supabase table
- Retain forever for MVP, revisit cleanup later

### Events Table

```sql
CREATE TABLE learning_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  session_id UUID,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_user ON learning_events(user_id, created_at);
CREATE INDEX idx_events_type ON learning_events(event_type, created_at);
```

### Event Catalog

#### Session Lifecycle (Emitter: Tutor Endpoint)

| Event | Payload |
|-------|---------|
| `session_started` | `user_id`, `session_id`, `timestamp` |
| `session_ended` | `user_id`, `session_id`, `timestamp`, `duration_minutes`, `message_count`, `total_tokens` |

Session timeout: **30 minutes** inactivity.

#### Learning Events (Emitter: Background Job)

| Event | Payload |
|-------|---------|
| `topic_introduced` | `user_id`, `session_id`, `topic`, `timestamp` |
| `topic_revisited` | `user_id`, `session_id`, `topic`, `prior_comprehension`, `timestamp` |
| `quiz_attempted` | `user_id`, `session_id`, `topic`, `question_summary`, `correct`, `attempts`, `timestamp` |
| `comprehension_updated` | `user_id`, `topic`, `old_level`, `new_level`, `timestamp` |

#### Behavioral Signals (Emitter: Background Job)

| Event | Payload |
|-------|---------|
| `frustration_detected` | `user_id`, `session_id`, `topic`, `context`, `timestamp` |
| `struggle_detected` | `user_id`, `session_id`, `topic`, `details`, `timestamp` |
| `breakthrough_moment` | `user_id`, `session_id`, `topic`, `details`, `timestamp` |
| `practice_requested` | `user_id`, `session_id`, `topic`, `timestamp` |

#### Profile Events (Emitter: API/Frontend)

| Event | Payload |
|-------|---------|
| `profile_updated` | `user_id`, `fields_updated`, `timestamp` |
| `goal_set` | `user_id`, `old_goal`, `new_goal`, `timestamp` |
| `preferences_changed` | `user_id`, `changes`, `timestamp` |

#### System Events (Emitter: Background Job)

| Event | Payload |
|-------|---------|
| `background_job_started` | `session_id`, `user_id`, `timestamp` |
| `background_job_completed` | `session_id`, `user_id`, `duration_ms`, `success`, `timestamp` |
| `background_job_failed` | `session_id`, `user_id`, `error`, `timestamp` |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     User (Frontend)                      │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │                 Tutor Endpoint                     │  │
│  │  - Loads user profile from Supabase               │  │
│  │  - Builds prompt (static sections + dynamic ctx)  │  │
│  │  - Limits topics to 10 most recent                │  │
│  │  - Calls Claude API                               │  │
│  │  - Emits session_started/session_ended events     │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │        Background Job (on session_ended)          │  │
│  │  - Pulls full transcript                          │  │
│  │  - Calls Claude for structured extraction         │  │
│  │  - Updates user_profiles table                    │  │
│  │  - Inserts quiz_attempts records                  │  │
│  │  - Emits learning/behavioral/system events        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      Supabase                            │
│  - conversations (chat history)                         │
│  - user_profiles (learning state)                       │
│  - quiz_attempts (detailed quiz history)                │
│  - learning_events (signals for analytics/future)       │
└─────────────────────────────────────────────────────────┘
```

---

## Future Expansion Points

When we validate the MVP works, these seams allow expansion:

| Current | Future | Expansion Path |
|---------|--------|----------------|
| Tutor handles quizzes inline | Separate Quiz Master agent | Extract quiz prompt section, add tool for quiz generation |
| Background Job extracts retrospectively | Real-time Lesson Planner | Subscribe to events, add mid-conversation interventions |
| Free-text topics | Topic taxonomy/graph | Build hierarchy from extracted topics, add prerequisite relationships |
| Append-only learning observations | Structured learning profile | Background Job reconciles observations into scores |
| 10 most recent topics | Semantic topic retrieval | Add embedding-based retrieval for relevant context |

---

## Tunable Parameters Summary

| Parameter | MVP Value | Adjust When |
|-----------|-----------|-------------|
| Recent sessions in profile | 3 | Tutor needs more/less context |
| Topics in Tutor context | 10 (most recent) | Context window issues or insufficient history |
| Session timeout | 30 min | User feedback on session boundaries |
| Comprehension scale | 1-5 | Need more/less granularity |
| Learning style reconciliation | None (append-only) | Observations become unwieldy |
| Extraction model | Test Sonnet vs Haiku | Cost vs quality tradeoff |
| Transcript format | JSON | A/B test if extraction quality issues |

---

## 5. Background Job Extraction Prompt

### Design Principles
- Model-agnostic (works with Claude, GPT, Gemini)
- JSON transcript format for unambiguous structure
- Rich profile context for better is_new/comprehension comparisons
- Explicit guidelines to reduce extraction variance

### System Prompt

Store the following as `EXTRACTION_SYSTEM_PROMPT` constant in your code:

```python
EXTRACTION_SYSTEM_PROMPT = """
## Role

You are an analytical system that processes tutoring conversation transcripts to extract structured learning insights. Your output updates the student's learning profile and tracks their progress.

## Input

You will receive:
1. A conversation transcript (JSON array of messages)
2. The student's current profile (existing topics, comprehension levels, learning observations, recent sessions)
3. Session metadata (start time, duration, message count)

## Output

Respond with ONLY a valid JSON object matching the schema below. No markdown, no explanation, no other text.

## Extraction Guidelines

### Session Summary
Write 2-4 sentences capturing:
- What was the main focus of the session?
- What progress was made?
- Any notable moments (breakthroughs, struggles, shifts in direction)?

For **mood**, assess the student's overall engagement:
- `engaged`: Active participation, asking questions, working through problems
- `confused`: Frequent clarification requests, hesitation, "I don't get it"
- `frustrated`: Expressions of difficulty, impatience, wanting to give up
- `confident`: Quick responses, teaching back correctly, ready to move on
- `neutral`: Hard to read, minimal emotional signals

### Topics Discussed
Extract distinct topics covered in the conversation.

**Granularity guidelines:**
- Topic names should be specific enough to be meaningful but general enough to recur
- "u-substitution" ✓ — specific, will recur
- "the integral we did at minute 5" ✗ — too specific
- "math" ✗ — too broad
- "calculus" — borderline, prefer more specific if possible

**is_new:** Compare against the student's existing topics in their profile. If this topic name (or a very close variant like "u-substitution" vs "u substitution") exists, it's NOT new.

**comprehension (1-5 scale):**
- 1: No understanding demonstrated, completely lost throughout
- 2: Struggling significantly, needed heavy guidance, many incorrect attempts
- 3: Getting it but shaky, needed some hints, partial understanding shown
- 4: Solid understanding, minimal help needed, correct with only minor errors
- 5: Mastery demonstrated, could explain to others, no assistance needed
- Use `null` if comprehension wasn't assessable (topic only briefly mentioned)

When assessing comprehension, compare against their prior level if the topic exists. Note improvement or regression in the notes field.

**notes:** Brief context that would help the tutor next time. Include comparisons to prior comprehension if relevant.

### Quiz Results
Identify moments where the tutor explicitly tested understanding.

**Include:**
- Formal quiz questions ("Let me check your understanding...")
- Direct knowledge checks with evaluation ("What would happen if...?" → student answers → tutor evaluates)
- Problem-solving exercises where correctness was assessed

**Do NOT include:**
- Rhetorical questions
- Casual back-and-forth conversation
- Questions the student asked the tutor
- Socratic questions without clear right/wrong evaluation

**Fields:**
- **question_summary**: Brief description of what was asked (not verbatim)
- **correct**: Did they ultimately get it right? (true even if hints were needed)
- **attempts**: How many tries before correct answer (1 = first attempt correct)
- **notes**: How they approached it, what hints were needed, confidence level

### Learning Style Observations
Note NEW patterns in how this student learns best.

**Only include observations that:**
- Are evident from THIS session specifically
- Would help personalize future tutoring
- Are specific and actionable
- Are NOT already captured in their existing learning style observations

**Good examples:**
- "Prefers to see worked examples before attempting problems"
- "Learns better when connecting concepts to real-world applications"
- "Gets overwhelmed when presented with multiple new concepts at once"
- "Benefits from drawing diagrams to visualize relationships"
- "Responds well to analogies comparing new concepts to familiar ones"

**Bad examples:**
- "Is a visual learner" (too vague, categorical)
- "Likes learning" (not actionable)
- "Struggled with derivatives" (this is comprehension, not learning style)
- "Asked good questions" (not a style pattern)

**Return an empty array if no new patterns emerged this session.**

### Open Questions
Capture questions that:
- The student asked but weren't fully resolved in this session
- Naturally arose as "what should we explore next" during discussion
- The tutor explicitly suggested exploring in a future session
- Represent gaps that became apparent

These become hooks for opening the next session.

### Suggested Next Topic
Based on the session flow, what should the next session focus on? Consider:
- Natural progression from what was covered
- Gaps or prerequisites that became apparent
- Student's expressed interests or goals
- Topics where comprehension is still low (levels 1-2)
- Open questions that point to specific topics

### Flags
Boolean signals for notable session events. **Err on the side of false** — only flag when clearly evident in the transcript.

- **user_expressed_frustration**: Explicit frustration statements ("This is so hard", "I give up", "I can't do this", "I hate this"). Mild difficulty doesn't count.
- **significant_struggle**: Extended difficulty (multiple failed attempts, long back-and-forth on one concept) that impacted session flow. Brief confusion doesn't count.
- **breakthrough_moment**: Clear "aha" moment — sudden understanding after struggle, explicit "Oh I get it now!", or dramatic improvement in responses.
- **requested_more_practice**: Student explicitly asked for more examples, practice problems, or exercises.

## Edge Cases

**Very short session (< 5 messages):**
- Summary should note the session was brief
- Topics may be empty or have `null` comprehension
- Most fields will be minimal — this is fine

**Off-topic/casual conversation:**
- Summary should note it was casual/off-topic
- Topics array should be empty
- Flags should all be false
- Not every session needs learning content

**Student seeking answers without understanding (homework help):**
- Note this pattern in the summary
- Comprehension may be low or `null` (unassessable)
- Note if tutor redirected toward teaching

**Returning to previously mastered topic:**
- Compare current performance to prior comprehension level
- Note if they've retained mastery or show regression
- Don't mark as breakthrough if they already knew it

## Output Schema

{
  "session_summary": {
    "date": "ISO 8601 timestamp of session start",
    "duration_minutes": <integer>,
    "summary": "<2-4 sentence summary>",
    "topics": ["<topic1>", "<topic2>"],
    "mood": "engaged | frustrated | confused | confident | neutral"
  },
  "topics_discussed": [
    {
      "name": "<topic name>",
      "is_new": <boolean>,
      "comprehension": <1-5 or null>,
      "notes": "<brief context for next session>"
    }
  ],
  "quiz_results": [
    {
      "topic": "<topic name>",
      "question_summary": "<what was asked>",
      "correct": <boolean>,
      "attempts": <integer>,
      "notes": "<how they approached it>"
    }
  ],
  "learning_style_observations": ["<observation1>", "<observation2>"],
  "open_questions": ["<question1>", "<question2>"],
  "suggested_next_topic": "<topic name>",
  "flags": {
    "user_expressed_frustration": <boolean>,
    "significant_struggle": <boolean>,
    "breakthrough_moment": <boolean>,
    "requested_more_practice": <boolean>
  }
}
"""
```

### Calling the Extraction

```python
import json
from typing import Protocol

# Model-agnostic interface
class LLMClient(Protocol):
    def complete(self, prompt: str, max_tokens: int) -> str: ...

def build_extraction_prompt(
    transcript: list[dict],
    profile: dict,
    metadata: dict
) -> str:
    # Format profile context
    existing_topics = profile.get('topics', {})
    topics_summary = {
        name: {
            "comprehension": data.get("comprehension"),
            "sessions_count": data.get("sessions_count"),
            "last_seen": data.get("last_seen")
        }
        for name, data in existing_topics.items()
    }
    
    return f"""
{EXTRACTION_SYSTEM_PROMPT}

---

## Student's Current Profile

**Display Name:** {profile.get('display_name', 'Unknown')}

**Learning Goals:** {profile.get('learning_goals', 'Not specified')}

**Existing Topics and Comprehension:**
```json
{json.dumps(topics_summary, indent=2, default=str)}
```

**Previous Learning Style Observations:**
{json.dumps(profile.get('learning_style_observations', []), indent=2)}

**Recent Sessions:**
{json.dumps(profile.get('recent_sessions', []), indent=2)}

---

## Session Metadata

- **Start Time:** {metadata['start_time']}
- **Duration:** {metadata['duration_minutes']} minutes
- **Message Count:** {metadata['message_count']}

---

## Conversation Transcript

```json
{json.dumps(transcript, indent=2)}
```

---

Now extract the structured insights as JSON:
"""

def extract_session_insights(
    client: LLMClient,
    transcript: list[dict],
    profile: dict,
    metadata: dict
) -> dict:
    prompt = build_extraction_prompt(transcript, profile, metadata)
    
    response = client.complete(prompt, max_tokens=2000)
    
    # Clean potential markdown wrapping
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    
    return json.loads(cleaned.strip())
```

### Provider-Specific Implementations

```python
# Claude
class ClaudeClient:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
    
    def complete(self, prompt: str, max_tokens: int) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

# OpenAI
class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    def complete(self, prompt: str, max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

# Gemini
class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def complete(self, prompt: str, max_tokens: int) -> str:
        response = self.model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens}
        )
        return response.text
```

### Testing Different Models

```python
# Easy to swap and compare
def test_extraction_models(transcript, profile, metadata):
    results = {}
    
    clients = {
        "claude-sonnet": ClaudeClient(ANTHROPIC_KEY, "claude-sonnet-4-20250514"),
        "claude-haiku": ClaudeClient(ANTHROPIC_KEY, "claude-haiku-4-20250514"),
        "gpt-4o": OpenAIClient(OPENAI_KEY, "gpt-4o"),
        "gpt-4o-mini": OpenAIClient(OPENAI_KEY, "gpt-4o-mini"),
        "gemini-pro": GeminiClient(GOOGLE_KEY, "gemini-1.5-pro"),
        "gemini-flash": GeminiClient(GOOGLE_KEY, "gemini-1.5-flash"),
    }
    
    for name, client in clients.items():
        try:
            results[name] = extract_session_insights(
                client, transcript, profile, metadata
            )
        except Exception as e:
            results[name] = {"error": str(e)}
    
    return results
```

### Evaluation Criteria

When comparing models, assess:

| Criterion | What to Look For |
|-----------|------------------|
| **Topic extraction** | Appropriate granularity? Consistent naming? |
| **is_new accuracy** | Correctly identifies topics in existing profile? |
| **Comprehension calibration** | Levels match actual performance in transcript? |
| **Quiz identification** | Finds real quizzes, ignores rhetorical questions? |
| **Learning style quality** | Specific and actionable? Not redundant with existing? |
| **Flag accuracy** | Triggers on clear signals, not over-sensitive? |
| **JSON validity** | Clean output, no markdown wrapping issues? |
| **Cost** | Tokens used, price per extraction |
| **Latency** | Time to complete |