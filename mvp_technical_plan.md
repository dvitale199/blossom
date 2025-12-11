# Blossom.ai MVP Technical Plan

## Executive Summary

Blossom.ai is an AI-powered learning platform that helps people systematically identify gaps in their knowledge and build personalized curricula to address them. The core thesis: **AI should make people smarter, not offload their thinking.**

This plan optimizes for **speed to learning** (getting real user feedback fast) while building abstractions that support the full vision: general learners, professionals, and students. The MVP focuses on **general learners** (curious adults exploring topics of interest) because that's where you have distribution—yourself and friends who want to learn things.

### Why General Learners First

| Factor | Student MVP | General Learner MVP |
|--------|-------------|---------------------|
| Distribution | Don't have it | You + friends |
| Can dogfood | No | Yes |
| Validation signal | Clear (grades) | Fuzzy (but solvable) |
| Knowledge structure | Constrained (syllabus) | Open (AI-generated) |
| Iteration speed | Slow (need users) | Fast (you are the user) |

A product you can use and iterate on beats a product with cleaner metrics that you can't test.

### North Star

Every feature decision filters through:

> **"Does this help the user understand more deeply, or does it let them avoid thinking?"**

Blossom succeeds when users demonstrably know more, not when they complete tasks faster.

---

## Product Context

### The Problem

Current AI tools optimize for answers, not understanding:
- Curious learners start courses but abandon them because content isn't calibrated to what they already know
- Professionals know they have skill gaps but lack structured paths to address them
- Students use ChatGPT to complete homework without learning

### Three Primary Use Cases

| Use Case | Knowledge Source | Assessment Signals | Timeline |
|----------|------------------|-------------------|----------|
| **General Learners** (MVP) | AI-generated from goal + grows with exploration | Quizzes, self-assessment | Self-paced |
| **Professionals** | Job descriptions, skill frameworks | Self-assessment, behavioral signals | Career goals |
| **Students** | Syllabus, coursework | Graded tests, quizzes | Semester/term |

### MVP User Journey

```
1. User creates a space: "I want to understand quantum mechanics"

2. AI generates initial knowledge map:
   - Core topics and subtopics
   - Dependencies between concepts
   - Suggested learning sequence
   - Estimated difficulty levels

3. User takes diagnostic quiz:
   - Identifies what they already know
   - Surfaces existing misconceptions
   - Calibrates starting point

4. User explores and learns:
   - Takes quizzes on specific topics
   - Optionally adds materials (articles, videos, books)
   - Self-assesses confidence on topics

5. System tracks understanding:
   - Assessment events from quizzes
   - Self-reported confidence
   - Gaps identified and prioritized

6. Adaptive practice:
   - Quizzes target weak areas
   - Questions calibrated to edge of knowledge
   - Progress visible on dashboard
```

---

## 1. Tech Stack Recommendation

### Frontend: **Next.js 14 + shadcn/ui + Tailwind**

**Why not Streamlit?** I know it's tempting given your experience, but Streamlit has real limitations for a consumer product:
- No fine-grained control over UX
- Session state management becomes painful
- File upload UX is clunky
- No offline/PWA capabilities
- Harder to add real-time features later

**Why Next.js specifically:**
- App Router gives you server components (great for AI streaming)
- API routes mean you could skip FastAPI initially if you want (but I don't recommend it)
- Vercel deployment is trivial
- shadcn/ui gives you beautiful, accessible components you copy-paste (not a dependency)
- Massive ecosystem = every problem has a solved example

**The learning curve trade-off:** You'll spend ~1-2 weeks getting comfortable, but the velocity payoff is worth it. Use v0.dev (Vercel's AI) to generate initial components.

### Backend: **FastAPI (your existing strength)**

No reason to change. FastAPI is:
- Excellent for AI workloads (async, streaming support)
- Great OpenAPI docs for your frontend integration
- You already know it well

**Key packages to add:**
- `python-multipart` for file uploads
- `celery` or `arq` for background jobs (document processing)
- `anthropic` SDK
- `PyMuPDF` (fitz) for PDF parsing
- `pydantic` v2 for validation

### Database: **Supabase (PostgreSQL + extras)**

**Why Supabase over raw Cloud SQL:**
- Gives you PostgreSQL (you know it)
- Includes auth
- Includes file storage
- Real-time subscriptions if you need them later
- Row Level Security for multi-tenant safety
- Generous free tier, predictable pricing
- Dashboard for debugging

**Why not a vector database?** 
You don't need one yet. PostgreSQL with `pgvector` extension (included in Supabase) handles similarity search fine for MVP scale.

**⚠️ Hard-to-reverse decision:** Database choice is sticky. PostgreSQL is safe—it's boring and that's good.

### File Storage: **Supabase Storage (backed by S3)**

Consolidating with your database provider simplifies operations.

### Auth: **Supabase Auth (included)**

**This is a strong "buy" decision.** Auth is:
- A solved problem with lots of edge cases
- A security liability if you build it wrong
- Not your differentiator

Supabase Auth gives you:
- Email/password, magic links, OAuth (Google)
- Session management
- JWT tokens that work with your FastAPI backend

### AI/LLM Layer: **Anthropic Claude API (primary)**

**Why Claude:**
- Excellent at structured extraction (knowledge maps)
- Strong at educational content generation
- Vision capabilities for OCR built-in
- Better at following complex instructions

**Cost control strategies:**
- Use Haiku for simple tasks (quiz answer evaluation)
- Use Sonnet for complex tasks (knowledge map generation, quiz creation)
- Cache aggressively
- Batch operations where possible

### Deployment: **Cloud Run (backend) + Vercel (frontend)**

**Why split:**
- Vercel is unmatched for Next.js DX
- Cloud Run you already know for Python workloads
- Both have generous free tiers
- Both scale to zero (cost control)

### Background Jobs: **Cloud Tasks → Cloud Run**

Knowledge map generation and material processing shouldn't block HTTP requests.

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  FRONTEND                                    │
│                           (Vercel / Next.js 14)                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Auth UI   │  │  Dashboard  │  │ Knowledge   │  │   Quiz Interface    │ │
│  │  (Supabase) │  │   + Gaps    │  │    Map      │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   BACKEND                                    │
│                            (Cloud Run / FastAPI)                            │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │   API Gateway    │  │  Auth Middleware │  │    Rate Limiting         │  │
│  │   (FastAPI)      │  │  (Supabase JWT)  │  │    (Memory)              │  │
│  └────────┬─────────┘  └──────────────────┘  └──────────────────────────┘  │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SERVICE LAYER                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │  Space      │  │  Knowledge  │  │    Quiz     │  │    Gap     │  │   │
│  │  │  Service    │  │   Service   │  │   Service   │  │   Engine   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │              UNDERSTANDING STATE TRACKER                       │  │   │
│  │  │  (Core IP: aggregates all signals into mastery estimates)     │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         AI PIPELINE                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │  Knowledge  │  │    Quiz     │  │  Response   │  │    Gap     │  │   │
│  │  │    Map      │  │  Generator  │  │  Evaluator  │  │  Analyzer  │  │   │
│  │  │  Generator  │  │             │  │             │  │            │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
         │                      │                           │
         ▼                      ▼                           ▼
┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────────────┐
│  Supabase       │  │   Cloud Tasks       │  │      Claude API             │
│  Storage        │  │   (Job Queue)       │  │                             │
│  (Files)        │  │                     │  │                             │
└─────────────────┘  └─────────────────────┘  └─────────────────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SUPABASE                                        │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌────────────────────┐   │
│  │     PostgreSQL      │  │    Auth Service     │  │   Realtime         │   │
│  │  (+ pgvector)       │  │                     │  │   (future)         │   │
│  └─────────────────────┘  └─────────────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core User Journey: Topic → Knowledge Map → Learning

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │ Frontend │     │ Backend  │     │   AI     │
│          │     │          │     │          │     │ Pipeline │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │
     │ "I want to     │                │                │
     │  learn X"      │                │                │
     │───────────────>│                │                │
     │                │                │                │
     │                │ POST /spaces   │                │
     │                │ {topic, goal}  │                │
     │                │───────────────>│                │
     │                │                │                │
     │                │                │ Generate map   │
     │                │                │───────────────>│
     │                │                │                │
     │                │                │  Claude:       │
     │                │                │  - Core topics │
     │                │                │  - Dependencies│
     │                │                │  - Sequence    │
     │                │                │  - Difficulty  │
     │                │                │                │
     │                │                │<───────────────│
     │                │                │                │
     │                │  Knowledge Map │                │
     │                │<───────────────│                │
     │                │                │                │
     │  Display Map   │                │                │
     │<───────────────│                │                │
     │                │                │                │
     │ Start Quiz     │                │                │
     │───────────────>│                │                │
     │                │                │                │
     │                │ GET /quiz      │                │
     │                │ (diagnostic)   │                │
     │                │───────────────>│                │
     │                │                │                │
     │                │                │ Generate Qs    │
     │                │                │───────────────>│
     │                │                │                │
     │                │  Quiz          │                │
     │                │<───────────────│                │
     │                │                │                │
     │  Take Quiz     │                │                │
     │<───────────────│                │                │
     │                │                │                │
     │ Submit Answers │                │                │
     │───────────────>│                │                │
     │                │                │                │
     │                │ POST /responses│                │
     │                │───────────────>│                │
     │                │                │                │
     │                │                │ Evaluate       │
     │                │                │───────────────>│
     │                │                │                │
     │                │                │ Update mastery │
     │                │                │ Identify gaps  │
     │                │                │                │
     │                │  Results +     │                │
     │                │  Updated Map   │                │
     │                │<───────────────│                │
     │                │                │                │
     │  See progress, │                │                │
     │  gaps, next    │                │                │
     │  steps         │                │                │
     │<───────────────│                │                │
```

---

## 3. Build vs. Buy Decisions

| Component | Decision | Reasoning |
|-----------|----------|-----------|
| **Authentication** | 🛒 BUY (Supabase Auth) | Security-critical, solved problem |
| **Database hosting** | 🛒 BUY (Supabase) | Ops burden not worth it |
| **File storage** | 🛒 BUY (Supabase Storage) | Commodity infrastructure |
| **Knowledge map generation** | 🔨 BUILD (custom prompts) | **Core differentiator** |
| **Understanding state tracker** | 🔨 BUILD (custom logic) | **Core differentiator** |
| **Quiz generation** | 🔨 BUILD (custom prompts) | **Core differentiator** |
| **Gap analysis** | 🔨 BUILD (custom logic + LLM) | **Core differentiator** |
| **PDF parsing** | 🔨 BUILD (PyMuPDF + Claude Vision) | For optional material uploads |
| **Analytics** | 🛒 BUY (PostHog) | Free tier sufficient |
| **Error monitoring** | 🛒 BUY (Sentry) | Essential, free tier |
| **LLM observability** | 🛒 BUY (Langfuse) | Critical for debugging AI |

---

## 4. Data Model

The data model supports the general learner MVP while anticipating professionals and students. Key design decisions:

- **Spaces** are topic-first, not document-first
- **Knowledge maps** can be AI-generated or document-sourced
- **Assessment signals** are polymorphic—quizzes, self-assessment, and future signals all feed the same mastery calculation
- **Gaps** are first-class entities with priority

### Entity Relationship Diagram

```
┌─────────────────────────────┐       ┌─────────────────────────────────┐
│          users              │       │            spaces               │
├─────────────────────────────┤       ├─────────────────────────────────┤
│ id (PK)                     │───┐   │ id (PK)                         │
│ email                       │   │   │ user_id (FK)                    │──┐
│ name                        │   └──>│ name                            │  │
│ created_at                  │       │ context_type (enum)             │  │
│ settings (JSONB)            │       │ topic (text) ← NEW              │  │
└─────────────────────────────┘       │ goal (text)                     │  │
                                      │ timeline_end (date, optional)   │  │
                                      │ created_at                      │  │
                                      │ settings (JSONB)                │  │
                                      └─────────────────────────────────┘  │
                                                    │                      │
context_type enum:                   ┌──────────────┴──────────────────────┤
 - exploratory (MVP)                 │                                     │
 - professional (future)             │                                     │
 - academic (future)                 ▼                                     │
                              ┌─────────────────────────────────┐          │
                              │          documents              │          │
                              ├─────────────────────────────────┤          │
                              │ id (PK)                         │          │
                              │ space_id (FK)                   │<─────────┘
                              │ document_type (enum)            │
                              │ original_filename               │
                              │ storage_path                    │
                              │ extracted_text                  │
                              │ processing_status               │
                              │ created_at                      │
                              │ metadata (JSONB)                │
                              └─────────────────────────────────┘
                                              │
document_type enum:                           │ (optional: enriches map)
 - article                                    │
 - book_excerpt                               ▼
 - video_notes                 ┌─────────────────────────────────┐
 - self_authored               │        knowledge_maps           │
 - syllabus (future)           ├─────────────────────────────────┤
 - job_description (future)    │ id (PK)                         │
                               │ space_id (FK)                   │
                               │ source_type (enum) ← NEW        │
                               │ source_document_id (FK, nullable)│
                               │ version                         │
                               │ is_active                       │
                               │ created_at                      │
                               └─────────────────────────────────┘
                                              │
source_type enum:                             │
 - ai_generated (MVP)                         │ (contains many)
 - document_extracted (future)                ▼
 - user_created (future)      ┌─────────────────────────────────┐
                              │           topics                │
                              ├─────────────────────────────────┤
                              │ id (PK)                         │
                              │ knowledge_map_id (FK)           │
                              │ parent_topic_id (FK, self-ref)  │◄───┐
                              │ name                            │    │
                              │ description                     │    │
                              │ learning_objectives (text[])    │    │
                              │ sequence_order                  │    │
                              │ difficulty_level (1-5)          │    │
                              │ estimated_hours (optional)      │    │
                              │ metadata (JSONB)                │────┘
                              └─────────────────────────────────┘
                                              │
                       ┌──────────────────────┼──────────────────────┐
                       │                      │                      │
                       ▼                      ▼                      ▼
        ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
        │ topic_dependencies  │  │   topic_mastery     │  │        gaps         │
        ├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
        │ id (PK)             │  │ id (PK)             │  │ id (PK)             │
        │ topic_id (FK)       │  │ user_id (FK)        │  │ user_id (FK)        │
        │ depends_on_id (FK)  │  │ topic_id (FK)       │  │ topic_id (FK)       │
        │ strength (enum)     │  │ mastery_level (0-100)│ │ priority (1-10)     │
        └─────────────────────┘  │ confidence (0-1)    │  │ identified_at       │
                                 │ last_assessed_at    │  │ resolved_at         │
dependency_strength enum:        │ self_reported (0-100)│ │ source_event_id (FK)│
 - required                      │ UNIQUE(user,topic)  │  │ misconception       │
 - helpful                       └─────────────────────┘  │ remediation         │
 - related                                ▲               └─────────────────────┘
                                          │
                                          │ (updates mastery)
                                          │
                              ┌───────────┴───────────────────┐
                              │      assessment_events        │
                              ├───────────────────────────────┤
                              │ id (PK)                       │
                              │ user_id (FK)                  │
                              │ topic_id (FK)                 │
                              │ event_type (enum)             │
                              │ signal_strength (0-100)       │
                              │ is_positive (boolean)         │
                              │ source_id (UUID, polymorphic) │
                              │ ai_analysis (JSONB)           │
                              │ created_at                    │
                              └───────────────────────────────┘

event_type enum:
 - quiz_response (MVP)
 - self_assessment (MVP)
 - graded_test_question (future)
 - interaction_signal (future)


┌─────────────────────────────────┐
│           quizzes               │
├─────────────────────────────────┤
│ id (PK)                         │
│ space_id (FK)                   │
│ user_id (FK)                    │
│ quiz_type (enum)                │
│ target_topic_ids (UUID[])       │
│ created_at                      │
│ completed_at                    │
│ overall_score                   │
└─────────────────────────────────┘

quiz_type enum:
 - diagnostic (initial assessment)
 - practice (targeted learning)
 - review (spaced repetition, future)

              │
              ▼
┌─────────────────────────────────┐
│       quiz_questions            │
├─────────────────────────────────┤
│ id (PK)                         │
│ quiz_id (FK)                    │
│ topic_id (FK)                   │
│ question_type (enum)            │
│ question_text                   │
│ options (JSONB)                 │
│ correct_answer                  │
│ difficulty (1-5)                │
│ reasoning_required              │
│ sequence_order                  │
└─────────────────────────────────┘

question_type enum:
 - mcq (MVP)
 - short_answer (future)
 - explanation (future)

              │
              ▼
┌─────────────────────────────────┐
│       quiz_responses            │
├─────────────────────────────────┤
│ id (PK)                         │
│ question_id (FK)                │
│ user_answer                     │
│ is_correct                      │
│ ai_evaluation (JSONB)           │
│ feedback                        │
│ responded_at                    │
└─────────────────────────────────┘


┌─────────────────────────────────┐
│      self_assessments           │  ← NEW for general learners
├─────────────────────────────────┤
│ id (PK)                         │
│ user_id (FK)                    │
│ topic_id (FK)                   │
│ confidence_level (0-100)        │
│ notes (text, optional)          │
│ created_at                      │
└─────────────────────────────────┘
```

### Key Schema Decisions

**1. Spaces are topic-first:**
```sql
CREATE TABLE spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    context_type space_context NOT NULL DEFAULT 'exploratory',
    topic TEXT NOT NULL,  -- "Quantum mechanics", "Machine learning", etc.
    goal TEXT,            -- "Understand well enough to explain to others"
    timeline_end DATE,    -- Optional: "I want to learn this by X"
    created_at TIMESTAMPTZ DEFAULT now(),
    settings JSONB DEFAULT '{}'::jsonb
);
```

**2. Knowledge maps track their source:**
```sql
CREATE TYPE knowledge_map_source AS ENUM (
    'ai_generated',        -- MVP: Claude generates from topic
    'document_extracted',  -- Future: extracted from syllabus
    'user_created'         -- Future: manual creation
);

CREATE TABLE knowledge_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE,
    source_type knowledge_map_source NOT NULL DEFAULT 'ai_generated',
    source_document_id UUID REFERENCES documents(id),
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**3. Self-assessment is a first-class signal:**
```sql
CREATE TABLE self_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    confidence_level INT CHECK (confidence_level BETWEEN 0 AND 100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Self-assessments create assessment_events
-- with event_type = 'self_assessment'
```

**4. Topics have learning objectives:**
```sql
-- For general learners, we need to be explicit about
-- what "understanding this topic" means
CREATE TABLE topics (
    -- ...
    learning_objectives TEXT[],  -- ["Explain X", "Apply Y to Z", "Distinguish A from B"]
    estimated_hours NUMERIC(4,1), -- Optional time estimate
    -- ...
);
```

**5. Mastery includes self-reported confidence:**
```sql
CREATE TABLE topic_mastery (
    -- ...
    mastery_level INT DEFAULT 0,     -- Calculated from assessments
    confidence NUMERIC(3,2) DEFAULT 0, -- Statistical confidence in estimate
    self_reported INT,                -- Last self-assessment (0-100)
    -- ...
);
```

---

## 5. AI Pipeline Design

### Pipeline Architecture

The key difference from the student flow: **knowledge maps are generated from topics, not extracted from documents.**

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           AI PIPELINE COMPONENTS                            │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: KNOWLEDGE MAP GENERATION (from topic)                  ← NEW FLOW │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Parse     │───>│  Generate   │───>│   Infer     │───>│   Store     │  │
│  │   Topic &   │    │   Topics    │    │Dependencies │    │   Map       │  │
│  │   Goal      │    │             │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Input: "I want to understand quantum mechanics"                            │
│  Output: Structured knowledge map with ~10-30 topics                        │
│                                                                             │
│  Models: Claude Sonnet - complex reasoning required                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: DIAGNOSTIC QUIZ GENERATION                                         │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Select    │───>│  Generate   │───>│  Validate   │                     │
│  │   Spanning  │    │  Questions  │    │  Quality    │                     │
│  │   Topics    │    │             │    │             │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
│  Goal: Quickly assess existing knowledge across the map                     │
│  Strategy: 1-2 questions per major topic area, varying difficulty          │
│                                                                             │
│  Models: Claude Sonnet                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: RESPONSE EVALUATION + MASTERY UPDATE                               │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Receive   │───>│  Evaluate   │───>│   Create    │───>│  Recalc     │  │
│  │   Answer    │    │ Correctness │    │  Assessment │    │  Mastery    │  │
│  │             │    │             │    │   Event     │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Models: Claude Haiku for MCQ (simple); Sonnet for open-ended (future)     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: GAP IDENTIFICATION & PRIORITIZATION                                │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │  Identify   │───>│  Prioritize │───>│  Generate   │                     │
│  │   Gaps      │    │  by Goal &  │    │ Remediation │                     │
│  │             │    │ Dependencies│    │    Hint     │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
│  Priority factors:                                                          │
│   - Is this foundational? (blocks other topics)                            │
│   - User's stated goal alignment                                           │
│   - Current mastery vs. target                                             │
│                                                                             │
│  Models: Mostly algorithmic; LLM for remediation suggestions                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: TARGETED QUIZ GENERATION                                           │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Select    │───>│  Generate   │───>│  Validate   │                     │
│  │   Gap       │    │  Questions  │    │  North Star │                     │
│  │   Topics    │    │             │    │             │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
│  Questions must:                                                            │
│   - Test understanding, not recall                                         │
│   - Target edge of current knowledge                                       │
│   - Surface misconceptions                                                 │
│                                                                             │
│  Models: Claude Sonnet                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: MATERIAL INTEGRATION (Optional)                                    │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Parse     │───>│   Match to  │───>│   Enrich    │                     │
│  │   Document  │    │   Topics    │    │   Topics    │                     │
│  │             │    │             │    │             │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
│  User uploads article/notes → enriches existing knowledge map               │
│  Can also suggest new topics to add                                        │
│                                                                             │
│  Models: Claude Haiku for classification                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Example Prompts (Core IP)

**Knowledge Map Generation (Stage 1):**
```python
KNOWLEDGE_MAP_GENERATION_PROMPT = """
You are helping someone build a structured learning path for a topic they want to understand deeply.

<learning_request>
Topic: {topic}
Goal: {goal}
Current background: {background}  # Optional: what they already know
Time available: {time_commitment}  # Optional: "a few hours a week"
</learning_request>

Generate a comprehensive knowledge map as JSON:

1. **topics**: Array of concepts to learn (aim for 15-30 topics)
   - name: Clear, specific topic name
   - description: What understanding this topic means (2-3 sentences)
   - learning_objectives: Array of 2-4 specific things they should be able to do
     (use verbs: "explain", "apply", "distinguish", "predict", "analyze")
   - sequence_order: Suggested learning order (1, 2, 3...)
   - difficulty_level: 1-5 scale relative to the overall topic
   - estimated_hours: Rough time to achieve basic understanding
   - parent_topic: Name of parent topic if this is a subtopic, null otherwise

2. **dependencies**: Array of topic relationships
   - topic: Topic name
   - depends_on: Array of prerequisite topic names
   - strength: required (must know first) | helpful (easier if known) | related (connected but independent)

3. **suggested_starting_points**: Array of 2-3 topic names
   - Good entry points based on typical prior knowledge
   - Should have minimal prerequisites

Design principles:
- Each topic should be learnable in 1-4 hours of focused study
- Topics should be specific enough to assess ("Wave-particle duality" not "Quantum weirdness")
- Learning objectives should be measurable through questions
- Include both foundational concepts and interesting applications
- Consider common misconceptions that should be addressed

Respond ONLY with valid JSON matching this schema:
{schema}
"""
```

**Diagnostic Quiz Generation (Stage 2):**
```python
DIAGNOSTIC_QUIZ_PROMPT = """
Generate a diagnostic quiz to assess someone's existing knowledge of a topic.

<knowledge_map>
{knowledge_map_json}
</knowledge_map>

<context>
Topic: {topic}
Goal: {goal}
</context>

Generate {num_questions} multiple-choice questions that:

1. **Span the knowledge map**: Cover different areas, not just one subtopic
2. **Vary in difficulty**: Mix easy (1-2), medium (3), and hard (4-5) questions
3. **Reveal understanding patterns**: Help identify which areas need work
4. **Test concepts, not trivia**: Focus on understanding, not memorization

For each question:
- question_text: Clear question testing a concept
- topic_id: Which topic this assesses
- options: Array of 4 options (A, B, C, D)
- correct_answer: The correct option letter
- difficulty: 1-5
- diagnostic_value: What getting this right/wrong tells us about understanding

Distribution:
- 30% foundational (prerequisites, basics)
- 50% core concepts (main topics)
- 20% advanced/application (synthesis, edge cases)

Respond ONLY with valid JSON.
"""
```

**Targeted Quiz Generation (Stage 5) — North Star Aligned:**
```python
TARGETED_QUIZ_PROMPT = """
Generate quiz questions that test genuine understanding, not just recall.

<topic>
Name: {topic_name}
Description: {topic_description}
Learning objectives: {learning_objectives}
</topic>

<user_context>
Current mastery: {mastery_level}/100
Known misconceptions: {known_misconceptions}
Self-reported confidence: {self_reported_confidence}
</user_context>

<knowledge_context>
Prerequisites: {prerequisite_topics}
This enables: {dependent_topics}
</knowledge_context>

Generate {num_questions} multiple-choice questions following these principles:

1. **Test understanding, not recall**
   - Ask "why does X happen" not "what is X"
   - Ask "what would change if" not "list the properties of"
   - Ask "which explanation is correct" not "which term matches"

2. **Target the edge of knowledge**
   - Current mastery is {mastery_level}%
   - Questions should be challenging but achievable
   - Too easy = no learning signal; too hard = discouraging

3. **Surface misconceptions**
   - Wrong answers should be tempting if you have common misunderstandings
   - Each distractor should represent a specific type of error

4. **Require reasoning**
   - The answer should not be obvious without thinking through the concept
   - Pattern matching or keyword spotting should not work

For each question:
- question_text: Clear, specific question
- options: Array of 4 options (A, B, C, D)
- correct_answer: The correct option letter
- difficulty: 1-5
- tests_objective: Which learning objective this assesses
- reasoning_required: What thinking process is needed
- misconception_tested: What wrong answer B/C/D test for

⚠️ QUALITY CHECK: Before including a question, ask:
"Could someone answer this correctly just by recognizing keywords or patterns?"
If yes, rewrite the question.

Respond ONLY with valid JSON.
"""
```

**Self-Assessment Processing:**
```python
SELF_ASSESSMENT_PROMPT = """
A learner has self-assessed their understanding of a topic. Help calibrate this.

<topic>
Name: {topic_name}
Learning objectives: {learning_objectives}
</topic>

<self_assessment>
Confidence level: {confidence_level}/100
Notes: {notes}
</self_assessment>

<quiz_history>
Recent quiz performance on this topic:
{quiz_performance_summary}
</quiz_history>

Analyze the calibration between self-reported confidence and demonstrated performance.

Return JSON:
{
  "calibration": "overconfident" | "underconfident" | "well_calibrated",
  "adjusted_estimate": 0-100,  // Your best estimate of actual mastery
  "reasoning": "Brief explanation",
  "suggested_action": "What they should do next",
  "clarifying_questions": ["Optional questions to better assess understanding"]
}
"""
```

### Pipeline Implementation

```python
# services/ai_pipeline.py

class AIPipeline:
    def __init__(self):
        self.client = Anthropic()
    
    async def generate_knowledge_map(
        self,
        topic: str,
        goal: str,
        background: str = None,
        time_commitment: str = None
    ) -> dict:
        """Generate a knowledge map from a topic description."""
        
        prompt = KNOWLEDGE_MAP_GENERATION_PROMPT.format(
            topic=topic,
            goal=goal,
            background=background or "Not specified",
            time_commitment=time_commitment or "Flexible",
            schema=KNOWLEDGE_MAP_SCHEMA
        )
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,  # Knowledge maps can be large
            messages=[{"role": "user", "content": prompt}]
        )
        
        self._log_usage("generate_knowledge_map", response.usage)
        return self._parse_and_validate(response.content[0].text, "knowledge_map")
    
    async def generate_diagnostic_quiz(
        self,
        knowledge_map: dict,
        topic: str,
        goal: str,
        num_questions: int = 10
    ) -> list:
        """Generate a diagnostic quiz spanning the knowledge map."""
        
        prompt = DIAGNOSTIC_QUIZ_PROMPT.format(
            knowledge_map_json=json.dumps(knowledge_map),
            topic=topic,
            goal=goal,
            num_questions=num_questions
        )
        
        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        questions = self._parse_and_validate(response.content[0].text, "quiz")
        return [q for q in questions if self._validates_north_star(q)]
    
    async def evaluate_response(
        self,
        question: dict,
        user_answer: str
    ) -> dict:
        """Evaluate a quiz response. Use Haiku for MCQ."""
        
        # MCQ is simple enough for Haiku
        is_correct = user_answer.upper() == question["correct_answer"].upper()
        
        # For MCQ, we can determine correctness without LLM
        # But we use LLM for feedback generation
        if is_correct:
            feedback = "Correct!"
            signal_strength = 80 + (question["difficulty"] * 4)  # 84-100
        else:
            # Generate helpful feedback
            feedback = await self._generate_feedback(question, user_answer)
            signal_strength = max(0, 50 - (question["difficulty"] * 10))  # 0-40
        
        return {
            "is_correct": is_correct,
            "feedback": feedback,
            "signal_strength": signal_strength,
            "is_positive": is_correct
        }
    
    def _validates_north_star(self, question: dict) -> bool:
        """Check if question aligns with 'understanding over recall' principle."""
        
        recall_phrases = [
            "what is the definition",
            "name the",
            "list the",
            "when was",
            "who discovered",
            "what year"
        ]
        question_lower = question["question_text"].lower()
        
        if any(phrase in question_lower for phrase in recall_phrases):
            return False
        
        if not question.get("reasoning_required"):
            return False
        
        return True
```

---

## 6. Cost Estimation Approach

### Per-User Cost Model (General Learner)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MONTHLY COST PER ACTIVE USER                         │
└─────────────────────────────────────────────────────────────────────────────┘

Assumptions (General Learner):
- 2 new spaces/month (new topics to learn)
- 2 diagnostic quizzes/month (10 questions each)
- 15 practice quizzes/month (5 questions each)
- 90 quiz responses evaluated/month
- 5 self-assessments/month
- 1 material upload/month (optional)

┌────────────────────┬──────────────┬────────────┬──────────┬───────────────┐
│ Operation          │ Model        │ Tokens/op  │ Ops/mo   │ Cost/mo       │
├────────────────────┼──────────────┼────────────┼──────────┼───────────────┤
│ Knowledge map gen  │ Sonnet       │ ~6K out    │ 2        │ $0.54         │
│ Diagnostic quiz    │ Sonnet       │ ~3K out    │ 2        │ $0.27         │
│ Practice quiz gen  │ Sonnet       │ ~2K out    │ 4*       │ $0.36         │
│ Response eval      │ Haiku        │ ~300 out   │ 90       │ $0.27         │
│ Self-assess calib  │ Haiku        │ ~500 out   │ 5        │ $0.03         │
│ Material process   │ Haiku        │ ~2K out    │ 1        │ $0.02         │
├────────────────────┼──────────────┼────────────┼──────────┼───────────────┤
│ TOTAL              │              │            │          │ ~$1.50/user   │
└────────────────────┴──────────────┴────────────┴──────────┴───────────────┘

* 15 quizzes but with caching, only ~4 new generations needed

Pricing:
- Claude Sonnet: $3/1M input, $15/1M output
- Claude Haiku: $0.25/1M input, $1.25/1M output
```

### Infrastructure Costs (Monthly)

| Service | Tier | Est. Cost |
|---------|------|-----------|
| Supabase | Pro | $25 |
| Vercel | Pro | $20 |
| Cloud Run | Pay-per-use | $10-30 |
| Sentry | Free | $0 |
| Langfuse | Free/Hobby | $0-25 |
| **Total Fixed** | | **~$55-100/mo** |

At $1.50 AI cost per user + ~$75 fixed costs:
- 10 users (you + friends): $90/mo
- 50 users: $150/mo ($3/user)
- 200 users: $375/mo ($1.88/user)

---

## 7. MVP Cut Decisions

### What to Build for MVP

| Feature | Include? | Reasoning |
|---------|----------|-----------|
| Account creation + Google OAuth | ✅ Yes | Core requirement |
| Create space from topic | ✅ Yes | **Core flow** |
| AI-generated knowledge map | ✅ Yes | **Core value prop** |
| Diagnostic quiz | ✅ Yes | Establishes baseline |
| Practice quizzes (MCQ) | ✅ Yes | Immediate value |
| Self-assessment on topics | ✅ Yes | Key signal for general learners |
| Mastery tracking + dashboard | ✅ Yes | Shows progress |
| Gap identification | ✅ Yes | Core value prop |
| Quiz targeting gaps | ✅ Yes | Closes the loop |

### What to Defer (and Why)

| Feature | Why It's Tempting | Why to Defer |
|---------|-------------------|--------------|
| **Document uploads** | Enriches learning | Optional for MVP; topic-first is enough |
| **Knowledge map editing** | Users might want control | Complex UX; see if AI maps are good enough |
| **Open-ended questions** | Better signal | Evaluation is harder, costs more |
| **Explanations/lessons** | Complete learning loop | Focus on assessment first; external resources exist |
| **Mobile app** | Learn on the go | PWA is enough |
| **Spaced repetition** | Proven effective | Need baseline data first |
| **Professional context** | Part of vision | Different enough to defer |
| **Student/syllabus context** | Part of vision | Need distribution first |
| **Social/sharing** | Motivation | Single-player first |
| **Notifications/reminders** | Engagement | Manual usage first |

### Your MVP Success Metrics

Without grades, you need proxy signals. Track these:

1. **Return rate**: Users who create a space and come back within 7 days
2. **Quiz completion**: Users who complete 5+ quizzes in a space
3. **Mastery movement**: Users whose mastery increases over time
4. **Self-reported value**: "Did this help you understand better?" (simple thumbs up/down)

The core question to validate:

> **"Do users who engage with Blossom actually understand topics better than they would have otherwise?"**

This is hard to measure directly, but proxies:
- They return (value signal)
- Their quiz performance improves (learning signal)
- They self-report understanding (subjective but useful)

---

## 8. First 30 Days Roadmap

```
Week 1: Foundation
├── Set up Supabase (db + auth + storage)
├── Set up Next.js with shadcn/ui
├── Basic auth flow (sign up, log in, Google OAuth)
├── Deploy to Vercel + Cloud Run (CI/CD)
└── Schema: users, spaces (with topic field)

Week 2: Knowledge Map Generation
├── "Create space" flow: enter topic + goal
├── AI pipeline: generate knowledge map from topic
├── Store: knowledge_maps, topics, topic_dependencies
├── Display: knowledge map as tree/list view
└── Basic space dashboard

Week 3: Assessment Loop
├── Diagnostic quiz generation
├── Quiz taking interface (MCQ)
├── Response evaluation
├── Assessment events + mastery calculation
├── Self-assessment UI ("How confident are you?")
└── Schema: quizzes, quiz_questions, quiz_responses, assessment_events, topic_mastery, self_assessments

Week 4: Gaps + Polish
├── Gap identification from low mastery
├── Gap display on dashboard
├── Targeted quiz generation (focus on gaps)
├── Progress visualization
├── Dogfood with yourself + 2-3 friends
└── Bug fixes, UX polish
```

---

## Appendix: Supabase Schema (SQL)

```sql
-- Enable pgvector for future embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Enums
CREATE TYPE space_context AS ENUM ('exploratory', 'professional', 'academic');
CREATE TYPE knowledge_map_source AS ENUM ('ai_generated', 'document_extracted', 'user_created');
CREATE TYPE document_type AS ENUM ('article', 'book_excerpt', 'video_notes', 'self_authored', 'syllabus', 'job_description');
CREATE TYPE processing_status AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE dependency_strength AS ENUM ('required', 'helpful', 'related');
CREATE TYPE assessment_event_type AS ENUM ('quiz_response', 'self_assessment', 'graded_test_question', 'interaction_signal');
CREATE TYPE question_type AS ENUM ('mcq', 'short_answer', 'explanation');
CREATE TYPE quiz_type AS ENUM ('diagnostic', 'practice', 'review');

-- Core tables
CREATE TABLE spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    context_type space_context NOT NULL DEFAULT 'exploratory',
    topic TEXT NOT NULL,
    goal TEXT,
    timeline_end DATE,
    created_at TIMESTAMPTZ DEFAULT now(),
    settings JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE,
    document_type document_type NOT NULL,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT,
    extracted_text TEXT,
    processing_status processing_status DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE knowledge_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE,
    source_type knowledge_map_source NOT NULL DEFAULT 'ai_generated',
    source_document_id UUID REFERENCES documents(id),
    version INT DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    knowledge_map_id UUID REFERENCES knowledge_maps(id) ON DELETE CASCADE,
    parent_topic_id UUID REFERENCES topics(id),
    name TEXT NOT NULL,
    description TEXT,
    learning_objectives TEXT[],
    sequence_order INT,
    difficulty_level INT CHECK (difficulty_level BETWEEN 1 AND 5),
    estimated_hours NUMERIC(4,1),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE topic_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    depends_on_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    strength dependency_strength NOT NULL,
    UNIQUE(topic_id, depends_on_id)
);

CREATE TABLE topic_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    mastery_level INT DEFAULT 0 CHECK (mastery_level BETWEEN 0 AND 100),
    confidence NUMERIC(3,2) DEFAULT 0 CHECK (confidence BETWEEN 0 AND 1),
    self_reported INT CHECK (self_reported BETWEEN 0 AND 100),
    last_assessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, topic_id)
);

CREATE TABLE assessment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    event_type assessment_event_type NOT NULL,
    signal_strength INT CHECK (signal_strength BETWEEN 0 AND 100),
    is_positive BOOLEAN NOT NULL,
    source_id UUID,
    ai_analysis JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    priority INT CHECK (priority BETWEEN 1 AND 10),
    identified_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    source_event_id UUID REFERENCES assessment_events(id),
    misconception TEXT,
    remediation TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(user_id, topic_id)
);

CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    quiz_type quiz_type NOT NULL,
    target_topic_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    overall_score INT
);

CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id),
    question_type question_type NOT NULL DEFAULT 'mcq',
    question_text TEXT NOT NULL,
    options JSONB,
    correct_answer TEXT NOT NULL,
    difficulty INT CHECK (difficulty BETWEEN 1 AND 5),
    reasoning_required TEXT,
    tests_objective TEXT,
    misconception_tested TEXT,
    sequence_order INT
);

CREATE TABLE quiz_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID REFERENCES quiz_questions(id) ON DELETE CASCADE,
    user_answer TEXT,
    is_correct BOOLEAN,
    ai_evaluation JSONB,
    feedback TEXT,
    responded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE self_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES topics(id) ON DELETE CASCADE,
    confidence_level INT CHECK (confidence_level BETWEEN 0 AND 100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_spaces_user ON spaces(user_id);
CREATE INDEX idx_topics_knowledge_map ON topics(knowledge_map_id);
CREATE INDEX idx_topic_mastery_user ON topic_mastery(user_id);
CREATE INDEX idx_assessment_events_user_topic ON assessment_events(user_id, topic_id, created_at DESC);
CREATE INDEX idx_gaps_user_active ON gaps(user_id) WHERE resolved_at IS NULL;
CREATE INDEX idx_quizzes_space ON quizzes(space_id);

-- Row Level Security
ALTER TABLE spaces ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own spaces"
    ON spaces FOR ALL USING (auth.uid() = user_id);

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access documents in their spaces"
    ON documents FOR ALL USING (
        space_id IN (SELECT id FROM spaces WHERE user_id = auth.uid())
    );

ALTER TABLE knowledge_maps ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access knowledge maps in their spaces"
    ON knowledge_maps FOR ALL USING (
        space_id IN (SELECT id FROM spaces WHERE user_id = auth.uid())
    );

ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access topics in their knowledge maps"
    ON topics FOR ALL USING (
        knowledge_map_id IN (
            SELECT km.id FROM knowledge_maps km
            JOIN spaces s ON km.space_id = s.id
            WHERE s.user_id = auth.uid()
        )
    );

ALTER TABLE topic_mastery ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own mastery"
    ON topic_mastery FOR ALL USING (auth.uid() = user_id);

ALTER TABLE assessment_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own events"
    ON assessment_events FOR ALL USING (auth.uid() = user_id);

ALTER TABLE gaps ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own gaps"
    ON gaps FOR ALL USING (auth.uid() = user_id);

ALTER TABLE quizzes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own quizzes"
    ON quizzes FOR ALL USING (auth.uid() = user_id);

ALTER TABLE quiz_questions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access questions in their quizzes"
    ON quiz_questions FOR ALL USING (
        quiz_id IN (SELECT id FROM quizzes WHERE user_id = auth.uid())
    );

ALTER TABLE quiz_responses ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access responses to their questions"
    ON quiz_responses FOR ALL USING (
        question_id IN (
            SELECT qq.id FROM quiz_questions qq
            JOIN quizzes q ON qq.quiz_id = q.id
            WHERE q.user_id = auth.uid()
        )
    );

ALTER TABLE self_assessments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own self assessments"
    ON self_assessments FOR ALL USING (auth.uid() = user_id);
```

---

## Summary of Changes from v2

| Aspect | v2 (Student MVP) | v3 (General Learner MVP) |
|--------|------------------|--------------------------|
| Primary flow | Upload syllabus → extract map | Enter topic → generate map |
| Knowledge map source | Document extraction | AI generation |
| Key assessment signal | Graded tests | Quizzes + self-assessment |
| Timeline | External (semester) | Self-paced (optional end date) |
| Document uploads | Core feature | Optional enrichment |
| Self-assessment | Future feature | **MVP feature** |
| Diagnostic quiz | Nice to have | **Core feature** |
| Target users | Students you don't have | You + friends |

The architecture is the same. The prompts and user flow changed. You can still build the student/syllabus path later—just add the document extraction prompts and change the space creation flow.