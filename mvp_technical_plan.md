# Blossom.ai MVP Technical Plan

## Executive Summary

This plan optimizes for **speed to learning** (getting real user feedback fast) while avoiding decisions that would be painful to reverse. Given your Python/GCP strengths and solo developer status, I'm recommending a stack that leans heavily on managed services for undifferentiated work while keeping your AI pipeline—your core differentiator—fully custom.

---

## 1. Tech Stack Recommendation

### Frontend: **Next.js 14 + shadcn/ui + Tailwind**

**Why not Streamlit?** I know it's tempting given your experience, but Streamlit has real limitations for a consumer product:
- No fine-grained control over UX (students/parents expect polish)
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

**Alternatives considered:**
- *Remix*: Great, but smaller ecosystem. Pick if you want more control over data loading.
- *SvelteKit*: Lovely DX, but React has more resources for when you're stuck.
- *Streamlit*: Only if you want to ship in <2 weeks and accept you'll rewrite the frontend.

### Backend: **FastAPI (your existing strength)**

No reason to change. FastAPI is:
- Excellent for AI workloads (async, streaming support)
- Great OpenAPI docs for your frontend integration
- You already know it well

**Key packages to add:**
- `python-multipart` for file uploads
- `celery` or `arq` for background jobs (document processing)
- `anthropic` or `openai` SDK
- `PyMuPDF` (fitz) for PDF parsing
- `pydantic` v2 for validation

### Database: **Supabase (PostgreSQL + extras)**

**Why Supabase over raw Cloud SQL:**
- Gives you PostgreSQL (you know it)
- Includes auth (see below)
- Includes file storage (see below)
- Real-time subscriptions if you need them later
- Row Level Security for multi-tenant safety
- Generous free tier, predictable pricing
- Dashboard for debugging

**Why not a vector database (Pinecone, Weaviate)?** 
You don't need one yet. PostgreSQL with `pgvector` extension (included in Supabase) handles similarity search fine for MVP scale. Don't add infrastructure complexity until you prove you need it.

**⚠️ Hard-to-reverse decision:** Database choice is sticky. PostgreSQL is safe—it's boring and that's good. If you started with MongoDB or a pure vector DB, migration would hurt.

### File Storage: **Supabase Storage (backed by S3)**

Consolidating with your database provider simplifies operations. Features you get:
- Signed URLs for secure uploads/downloads
- Image transformations (for thumbnails)
- Integrates with Row Level Security

Alternative: GCS is fine if you want to stay pure GCP. The integration work is similar.

### Auth: **Supabase Auth (included)**

**This is a strong "buy" decision.** Auth is:
- A solved problem with lots of edge cases
- A security liability if you build it wrong
- Not your differentiator

Supabase Auth gives you:
- Email/password, magic links, OAuth (Google is essential for students)
- Session management
- JWT tokens that work with your FastAPI backend
- User management UI

**Alternatives:**
- *Clerk*: More polished UI, better if you want social login profiles. Costs more.
- *Auth0*: Enterprise-grade, overkill for MVP.
- *Roll your own*: Don't. Seriously.

### AI/LLM Layer: **Anthropic Claude API (primary) + OpenAI (fallback)**

**Why Claude as primary:**
- Excellent at structured extraction (knowledge maps)
- Strong at educational content generation
- Vision capabilities for OCR built-in (no separate service needed!)
- Better at following complex instructions
- Slightly lower cost at Sonnet tier

**Architecture approach:**
```
User uploads PDF/image
    → Claude Vision extracts text + structure
    → Claude generates knowledge map JSON
    → Stored in PostgreSQL
    → Quiz generation pulls from knowledge map
    → Claude evaluates responses
```

**Why have OpenAI as fallback:**
- Redundancy if either API has issues
- Some tasks (embeddings) might be cheaper with `text-embedding-3-small`
- Students need reliability

**Cost control strategies (detailed in section 6):**
- Use Haiku for simple tasks (quiz answer evaluation)
- Cache aggressively
- Batch operations where possible

### Deployment: **Cloud Run (backend) + Vercel (frontend)**

**Why split:**
- Vercel is unmatched for Next.js DX (preview deploys, edge functions, analytics)
- Cloud Run you already know for Python workloads
- Both have generous free tiers
- Both scale to zero (cost control)

**Alternative:** Put everything on Cloud Run. Works fine, slightly more config for Next.js, but keeps you in one ecosystem.

### Background Jobs: **Cloud Run Jobs or Cloud Tasks**

Document processing shouldn't block HTTP requests. Options:
- *Cloud Tasks*: Queue that triggers Cloud Run endpoints. Simple, GCP-native.
- *Cloud Run Jobs*: For longer processing. Can run up to 24 hours.
- *Celery + Redis*: More complex but more control. Defer unless needed.

For MVP, Cloud Tasks → Cloud Run endpoint is simplest.

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
                                      │ HTTPS / WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                   BACKEND                                    │
│                            (Cloud Run / FastAPI)                            │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │   API Gateway    │  │  Auth Middleware │  │    Rate Limiting         │  │
│  │   (FastAPI)      │  │  (Supabase JWT)  │  │    (Redis/Memory)        │  │
│  └────────┬─────────┘  └──────────────────┘  └──────────────────────────┘  │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         SERVICE LAYER                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │  Document   │  │  Knowledge  │  │    Quiz     │  │    Gap     │  │   │
│  │  │  Service    │  │   Service   │  │   Service   │  │  Analyzer  │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         AI PIPELINE                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │   │
│  │  │   Parser    │  │  Extractor  │  │  Generator  │  │  Evaluator │  │   │
│  │  │ (PDF/Image) │  │ (Knowledge) │  │   (Quiz)    │  │ (Response) │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
         │                      │                           │
         ▼                      ▼                           ▼
┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────────────┐
│  Supabase       │  │   Cloud Tasks       │  │      Claude API             │
│  Storage        │  │   (Job Queue)       │  │      (+ OpenAI fallback)    │
│  (Files)        │  │                     │  │                             │
└─────────────────┘  └─────────────────────┘  └─────────────────────────────┘
         │                      │
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

### Core User Journey: Syllabus Upload → Knowledge Map

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │     │ Frontend │     │ Backend  │     │  Queue   │     │   AI     │
│          │     │          │     │          │     │          │     │ Pipeline │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │                │
     │ Upload PDF     │                │                │                │
     │───────────────>│                │                │                │
     │                │                │                │                │
     │                │ POST /documents│                │                │
     │                │───────────────>│                │                │
     │                │                │                │                │
     │                │                │ Store file     │                │
     │                │                │ (Supabase)     │                │
     │                │                │                │                │
     │                │                │ Queue job      │                │
     │                │                │───────────────>│                │
     │                │                │                │                │
     │                │  202 Accepted  │                │                │
     │                │<───────────────│                │                │
     │                │                │                │                │
     │  "Processing"  │                │                │                │
     │<───────────────│                │                │                │
     │                │                │                │ Process job    │
     │                │                │                │───────────────>│
     │                │                │                │                │
     │                │                │                │  1. Fetch PDF  │
     │                │                │                │  2. Claude     │
     │                │                │                │     Vision     │
     │                │                │                │  3. Extract    │
     │                │                │                │     structure  │
     │                │                │                │  4. Generate   │
     │                │                │                │     knowledge  │
     │                │                │                │     map        │
     │                │                │                │                │
     │                │                │  Store results │                │
     │                │                │<───────────────│                │
     │                │                │                │                │
     │                │ Poll/Subscribe │                │                │
     │                │───────────────>│                │                │
     │                │                │                │                │
     │                │  Knowledge Map │                │                │
     │                │<───────────────│                │                │
     │                │                │                │                │
     │  Display Map   │                │                │                │
     │<───────────────│                │                │                │
     │                │                │                │                │
```

---

## 3. Build vs. Buy Decisions

| Component | Decision | Reasoning |
|-----------|----------|-----------|
| **Authentication** | 🛒 BUY (Supabase Auth) | Security-critical, solved problem, not differentiating |
| **Database hosting** | 🛒 BUY (Supabase) | Ops burden not worth it for MVP |
| **File storage** | 🛒 BUY (Supabase Storage) | Commodity infrastructure |
| **PDF text extraction** | 🔨 BUILD (PyMuPDF + Claude Vision) | Claude Vision handles images/scans; PyMuPDF for clean PDFs. No need for separate OCR service |
| **Knowledge extraction** | 🔨 BUILD (custom prompts) | **Core differentiator**—your prompt engineering and schema design IS the product |
| **Quiz generation** | 🔨 BUILD (custom prompts) | Core differentiator |
| **Gap analysis** | 🔨 BUILD (custom logic + LLM) | Core differentiator |
| **Email/notifications** | 🛒 BUY (Resend or Supabase) | Start with transactional only, don't build |
| **Analytics** | 🛒 BUY (Vercel Analytics + PostHog) | Free tiers are sufficient |
| **Error monitoring** | 🛒 BUY (Sentry) | Essential, generous free tier |
| **LLM observability** | 🛒 BUY (Langfuse or Helicone) | Critical for debugging AI issues, cost tracking |

### Detailed Build Decisions

**PDF/Image Processing:**
```python
# Your processing logic (simplified)
async def process_document(file_path: str, file_type: str) -> str:
    if file_type == "application/pdf":
        # Try PyMuPDF first (fast, free)
        text = extract_with_pymupdf(file_path)
        if is_mostly_text(text):  # >80% extractable
            return text
        # Fall back to Claude Vision for scanned PDFs
        return await extract_with_claude_vision(file_path)
    
    elif file_type.startswith("image/"):
        # Always use Claude Vision for images
        return await extract_with_claude_vision(file_path)
    
    else:  # Plain text
        return read_file(file_path)
```

This hybrid approach saves money (PyMuPDF is free) while handling scanned documents gracefully.

---

## 4. Data Model

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────────┐
│     users       │       │       spaces        │
├─────────────────┤       ├─────────────────────┤
│ id (PK)         │───┐   │ id (PK)             │
│ email           │   │   │ user_id (FK)        │──┐
│ name            │   └──>│ name                │  │
│ created_at      │       │ subject             │  │
│ settings (JSON) │       │ semester            │  │
└─────────────────┘       │ created_at          │  │
                          │ settings (JSON)     │  │
                          └─────────────────────┘  │
                                    │              │
                 ┌──────────────────┴──────────────┤
                 │                                 │
                 ▼                                 │
┌─────────────────────────────────────┐           │
│            documents                 │           │
├─────────────────────────────────────┤           │
│ id (PK)                             │           │
│ space_id (FK)                       │<──────────┘
│ type (syllabus|material|test)       │
│ original_filename                   │
│ storage_path                        │
│ mime_type                           │
│ extracted_text                      │
│ processing_status                   │
│ processed_at                        │
│ created_at                          │
│ metadata (JSON)                     │
└─────────────────────────────────────┘
                 │
                 │ (syllabus documents generate)
                 ▼
┌─────────────────────────────────────┐
│          knowledge_maps             │
├─────────────────────────────────────┤
│ id (PK)                             │
│ space_id (FK)                       │
│ document_id (FK) (source syllabus)  │
│ version                             │
│ created_at                          │
│ is_active                           │
└─────────────────────────────────────┘
                 │
                 │ (contains many)
                 ▼
┌─────────────────────────────────────┐
│            topics                   │
├─────────────────────────────────────┤
│ id (PK)                             │
│ knowledge_map_id (FK)               │
│ name                                │
│ description                         │
│ sequence_order                      │
│ estimated_date (from syllabus)      │
│ is_milestone                        │
│ parent_topic_id (FK, self-ref)      │◄───┐
│ difficulty_level                    │    │
│ metadata (JSON)                     │────┘
└─────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌─────────────────┐   ┌─────────────────────────┐
│topic_dependencies│  │    topic_mastery        │
├─────────────────┤   ├─────────────────────────┤
│ id (PK)         │   │ id (PK)                 │
│ topic_id (FK)   │   │ user_id (FK)            │
│ depends_on (FK) │   │ topic_id (FK)           │
│ strength        │   │ mastery_level (0-100)   │
└─────────────────┘   │ confidence              │
                      │ last_assessed_at        │
                      │ assessment_count        │
                      │ is_gap                  │
                      │ gap_priority            │
                      └─────────────────────────┘

┌─────────────────────────────────────┐
│            quizzes                  │
├─────────────────────────────────────┤
│ id (PK)                             │
│ space_id (FK)                       │
│ user_id (FK)                        │
│ quiz_type (practice|diagnostic)     │
│ target_topics (FK[])                │
│ created_at                          │
│ completed_at                        │
│ overall_score                       │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│          quiz_questions             │
├─────────────────────────────────────┤
│ id (PK)                             │
│ quiz_id (FK)                        │
│ topic_id (FK)                       │
│ question_type (mcq|short|explain)   │
│ question_text                       │
│ options (JSON, for MCQ)             │
│ correct_answer                      │
│ difficulty                          │
│ sequence_order                      │
└─────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│          quiz_responses             │
├─────────────────────────────────────┤
│ id (PK)                             │
│ question_id (FK)                    │
│ user_answer                         │
│ is_correct                          │
│ ai_evaluation (JSON)                │
│ feedback                            │
│ responded_at                        │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│          graded_tests               │
├─────────────────────────────────────┤
│ id (PK)                             │
│ document_id (FK)                    │
│ space_id (FK)                       │
│ test_date                           │
│ total_score                         │
│ max_score                           │
│ ai_analysis (JSON)                  │
│ identified_gaps (topic_id[])        │
└─────────────────────────────────────┘
```

### Key Schema Decisions

**1. Knowledge maps are versioned:**
```sql
-- When syllabus is re-uploaded or edited, create new version
-- Keep old version for history but mark inactive
ALTER TABLE knowledge_maps ADD COLUMN version INT DEFAULT 1;
ALTER TABLE knowledge_maps ADD COLUMN is_active BOOLEAN DEFAULT true;
```

**2. Topics support hierarchy (for complex subjects):**
```sql
-- Self-referential for subtopics
-- "Calculus" → "Derivatives" → "Chain Rule"
parent_topic_id UUID REFERENCES topics(id)
```

**3. Mastery is per-user, per-topic:**
```sql
-- This is your core "progress" data
-- Updated after every quiz response
CREATE TABLE topic_mastery (
    user_id UUID REFERENCES users(id),
    topic_id UUID REFERENCES topics(id),
    mastery_level INT CHECK (mastery_level BETWEEN 0 AND 100),
    -- ...
    PRIMARY KEY (user_id, topic_id)
);
```

**4. JSON columns for flexibility:**
```sql
-- metadata, ai_evaluation, settings use JSONB
-- Lets you iterate on structure without migrations
-- PostgreSQL JSONB is queryable and indexable
metadata JSONB DEFAULT '{}'::jsonb
```

**⚠️ Hard-to-reverse decision:** Your knowledge map schema (topics, dependencies) will shape your entire product. Spend time getting this right. Consider:
- Can topics span multiple syllabi? (I'd say no for MVP—one syllabus = one knowledge map)
- How granular? (Err toward more specific: "Solving quadratic equations" not "Algebra")
- How do you handle syllabus updates mid-semester?

---

## 5. AI Pipeline Design

### Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           AI PIPELINE COMPONENTS                            │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: DOCUMENT INGESTION                                                 │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Upload    │───>│   Parse     │───>│  Normalize  │───>│   Store     │  │
│  │  Handler    │    │  (PyMuPDF/  │    │   Text      │    │  (Supabase) │  │
│  │             │    │   Vision)   │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Models: Claude Haiku (OCR) - cheap, fast for text extraction               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: KNOWLEDGE EXTRACTION (Syllabus Only)                               │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  Structure  │───>│   Topic     │───>│ Dependency  │───>│  Timeline   │  │
│  │  Detection  │    │ Extraction  │    │  Inference  │    │  Mapping    │  │
│  │             │    │             │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Models: Claude Sonnet - best balance of quality/cost for complex reasoning │
│                                                                             │
│  Output: Structured JSON matching your topics schema                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: MATERIAL INTEGRATION (Course materials, worksheets)                │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Match to  │───>│   Enrich    │───>│   Update    │                     │
│  │   Topics    │    │   Topics    │    │  Knowledge  │                     │
│  │             │    │ (examples,  │    │    Map      │                     │
│  │             │    │  context)   │    │             │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
│  Models: Claude Haiku - simpler classification task                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: ASSESSMENT (Graded tests → Gap identification)                     │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Extract   │───>│   Map to    │───>│  Analyze    │───>│   Update    │  │
│  │  Q&A Pairs  │    │   Topics    │    │   Errors    │    │  Mastery    │  │
│  │             │    │             │    │             │    │   + Gaps    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Models: Claude Sonnet - nuanced understanding of student errors            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: QUIZ GENERATION                                                    │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   Select    │───>│  Generate   │───>│  Validate   │                     │
│  │   Topics    │    │  Questions  │    │  Quality    │                     │
│  │ (gap-based) │    │             │    │             │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
│  Models: Claude Sonnet - quality questions require reasoning                │
│                                                                             │
│  Strategy: Generate 5-7 questions, validate, cache for reuse               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: RESPONSE EVALUATION                                                │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Receive   │───>│  Evaluate   │───>│  Generate   │───>│   Update    │  │
│  │   Answer    │    │ Correctness │    │  Feedback   │    │  Mastery    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Models: Claude Haiku - MCQ is simple; Sonnet for open-ended               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Example Prompts (Your Core IP)

**Knowledge Extraction Prompt (Stage 2):**
```python
SYLLABUS_EXTRACTION_PROMPT = """
You are analyzing a course syllabus to extract a structured knowledge map.

<syllabus>
{extracted_text}
</syllabus>

Extract the following as JSON:

1. **topics**: Array of learning topics/concepts
   - name: Clear, specific topic name
   - description: What students should understand
   - sequence_order: Order in the course (1, 2, 3...)
   - estimated_week: When this is covered (week number)
   - is_milestone: Is this a major exam/project? (boolean)
   - difficulty_level: 1-5 scale
   - parent_topic: Name of parent topic if this is a subtopic, null otherwise

2. **dependencies**: Array of topic relationships
   - topic: Topic name
   - depends_on: Array of prerequisite topic names
   - strength: How strong the dependency is (required|helpful|related)

3. **timeline**: Key dates
   - date: ISO date string
   - event: What happens (exam, project due, etc.)
   - related_topics: Array of relevant topic names

Be specific with topic names. "Solving quadratic equations by factoring" is better 
than "Algebra". Extract ALL assessments as milestones.

Respond ONLY with valid JSON matching this schema:
{schema}
"""
```

**Gap Analysis Prompt (Stage 4):**
```python
GAP_ANALYSIS_PROMPT = """
Analyze this graded test to identify knowledge gaps.

<test_content>
{extracted_test_content}
</test_content>

<knowledge_map>
{knowledge_map_json}
</knowledge_map>

For each question the student got wrong or partially wrong:
1. Identify which topic(s) from the knowledge map it tests
2. Analyze the specific misconception or gap
3. Rate severity (critical|moderate|minor)
4. Suggest what to review

Return JSON:
{
  "gaps": [
    {
      "topic_id": "uuid",
      "topic_name": "string",
      "misconception": "What the student seems to misunderstand",
      "severity": "critical|moderate|minor",
      "evidence": "Quote from test showing the error",
      "remediation": "What to study/practice"
    }
  ],
  "overall_assessment": "Brief summary of student's understanding"
}
"""
```

### Pipeline Implementation Pattern

```python
# services/ai_pipeline.py

from anthropic import Anthropic
from typing import Literal

class AIPipeline:
    def __init__(self):
        self.client = Anthropic()
        
    async def run_stage(
        self,
        stage: Literal["extract", "quiz_gen", "evaluate"],
        input_data: dict,
        model: str = "claude-sonnet-4-20250514"
    ) -> dict:
        """
        Generic stage runner with:
        - Retry logic
        - Cost tracking
        - Structured output validation
        """
        prompt = self._get_prompt(stage, input_data)
        
        # Track token usage for cost monitoring
        response = await self.client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Log to observability (Langfuse/Helicone)
        self._log_usage(stage, response.usage)
        
        # Parse and validate JSON response
        return self._parse_response(stage, response.content[0].text)
    
    def _select_model(self, stage: str, complexity: str) -> str:
        """Choose model based on task complexity and cost."""
        model_map = {
            ("extract_text", "any"): "claude-haiku-4-5-20251001",
            ("extract_knowledge", "any"): "claude-sonnet-4-20250514",
            ("evaluate", "mcq"): "claude-haiku-4-5-20251001",
            ("evaluate", "open"): "claude-sonnet-4-20250514",
            ("quiz_gen", "any"): "claude-sonnet-4-20250514",
        }
        return model_map.get((stage, complexity), "claude-sonnet-4-20250514")
```

---

## 6. Cost Estimation Approach

### Per-User Cost Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MONTHLY COST PER ACTIVE USER                         │
└─────────────────────────────────────────────────────────────────────────────┘

Assumptions:
- 1 syllabus upload (beginning of semester)
- 4 material uploads/month
- 2 graded test uploads/month  
- 20 quizzes taken/month (5 questions each = 100 questions)
- 100 quiz responses evaluated/month

┌────────────────────┬──────────────┬────────────┬──────────┬───────────────┐
│ Operation          │ Model        │ Tokens/op  │ Ops/mo   │ Cost/mo       │
├────────────────────┼──────────────┼────────────┼──────────┼───────────────┤
│ Syllabus extract   │ Sonnet       │ ~8K out    │ 0.25*    │ $0.12         │
│ Material process   │ Haiku        │ ~2K out    │ 4        │ $0.08         │
│ Test analysis      │ Sonnet       │ ~4K out    │ 2        │ $0.60         │
│ Quiz generation    │ Sonnet       │ ~3K out    │ 5**      │ $0.45         │
│ Response eval      │ Haiku        │ ~500 out   │ 100      │ $0.50         │
├────────────────────┼──────────────┼────────────┼──────────┼───────────────┤
│ TOTAL              │              │            │          │ ~$1.75/user   │
└────────────────────┴──────────────┴────────────┴──────────┴───────────────┘

* Amortized across ~4 months per semester
** 20 quizzes but with caching, only ~5 new generations needed

Pricing used (as of late 2024):
- Claude Sonnet: $3/1M input, $15/1M output
- Claude Haiku: $0.25/1M input, $1.25/1M output
```

### Cost Control Strategies

**1. Model Selection by Task:**
```python
# Map task complexity to model
MODEL_ROUTING = {
    "ocr_extraction": "haiku",      # Simple text extraction
    "mcq_evaluation": "haiku",      # Binary correct/incorrect
    "knowledge_extraction": "sonnet", # Complex reasoning
    "quiz_generation": "sonnet",     # Creative + accurate
    "gap_analysis": "sonnet",        # Nuanced understanding
}
```

**2. Aggressive Caching:**
```python
# Cache quiz questions by topic
# If topic hasn't changed and we have 10+ questions, don't regenerate
async def get_quiz_questions(topic_id: str, count: int) -> list:
    cached = await cache.get(f"quiz_questions:{topic_id}")
    if cached and len(cached) >= count:
        return random.sample(cached, count)
    
    # Generate new questions, add to cache
    new_questions = await ai_pipeline.generate_questions(topic_id, count=10)
    await cache.set(f"quiz_questions:{topic_id}", new_questions, ttl=86400*7)
    return new_questions[:count]
```

**3. Batch Processing:**
```python
# When processing multiple materials, batch into single API call
async def process_materials_batch(materials: list[Document]) -> list:
    combined_text = "\n---\n".join([m.extracted_text for m in materials])
    # Single API call instead of N calls
    result = await ai_pipeline.classify_materials_batch(combined_text)
    return result
```

**4. Token Budgets:**
```python
# Hard limits per operation
TOKEN_LIMITS = {
    "syllabus_extraction": 10000,
    "quiz_generation": 4000,
    "response_evaluation": 1000,
}

# Per-user monthly budget
USER_MONTHLY_BUDGET = 50000  # tokens
```

**5. Monitoring & Alerts:**
```python
# Track costs in real-time with Langfuse or custom
@track_cost
async def generate_quiz(topic_ids: list[str]) -> Quiz:
    ...

# Alert if user exceeds expected usage
if user.monthly_token_usage > USER_MONTHLY_BUDGET * 0.8:
    await notify_admin(f"User {user.id} at 80% budget")
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

At $1.75 AI cost per user + ~$75 fixed costs:
- 50 users: $162/mo ($3.25/user)
- 200 users: $425/mo ($2.12/user)
- 1000 users: $1,825/mo ($1.83/user)

---

## 7. MVP Cut Decisions

### What to Build for MVP

| Feature | Include? | Reasoning |
|---------|----------|-----------|
| Account creation | ✅ Yes | Core requirement |
| Spaces (per class) | ✅ Yes | Essential organization |
| Syllabus upload (PDF/image/text) | ✅ Yes | Core value prop |
| Knowledge map display | ✅ Yes | Core value prop |
| Material uploads | ✅ Yes | Enriches knowledge map |
| Graded test upload + gap ID | ✅ Yes | High value, differentiating |
| Basic quizzes (MCQ) | ✅ Yes | Immediate value |
| Progress dashboard | ✅ Yes | Shows value over time |
| Google OAuth | ✅ Yes | Students expect it |

### What to Defer (and Why)

| Feature | Why It's Tempting | Why to Defer |
|---------|-------------------|--------------|
| **Mobile app** | Students are on phones | PWA gives you 80% of mobile value. Native apps are 3x the maintenance. |
| **Open-ended quiz responses** | More pedagogically valuable | Evaluation is harder, costs more. Start with MCQ, add later. |
| **Parent dashboard** | Part of your vision | Different user, different needs. Nail student experience first. |
| **Study schedule generation** | Feels "smart" | Complex to get right. Manual timeline from syllabus is enough for MVP. |
| **Collaborative features** | Study groups are real | Multi-user is hard. Single-player first. |
| **Advanced visualizations** | Knowledge graphs look cool | Simple list/timeline is fine. Don't bikeshed on D3.js. |
| **Multiple choice answer explanations** | Better learning | Doubles generation cost. Add after you validate core. |
| **Spaced repetition scheduling** | Proven effective | Requires more data to do well. V2 feature. |
| **Integration with LMS (Canvas, etc.)** | Easier onboarding | API work is significant. Manual upload is fine for MVP. |
| **Real-time progress updates** | Feels modern | Polling every 30s is fine. WebSockets add complexity. |
| **Custom branding/white-label** | Future B2B play | Not relevant for consumer MVP. |
| **Offline mode** | Students study anywhere | Service worker complexity not worth it yet. |
| **Multi-language support** | Bigger market | i18n is a tax on every feature. English first. |

### The "One More Thing" Trap

These features feel small but aren't:
- **"Just add dark mode"** → Theme system, testing, edge cases
- **"Let users edit the knowledge map"** → Conflict resolution, versioning, UI complexity
- **"Show estimated study time"** → Needs calibration data you don't have
- **"Send reminder notifications"** → Notification infrastructure, preferences, timing logic

### Your MVP Success Metric

Before building anything else, prove:
> "Students who upload a syllabus and take 3+ quizzes return within 7 days"

If this isn't happening, adding features won't help.

---

## Summary: First 30 Days Roadmap

```
Week 1: Foundation
├── Set up Supabase (db + auth + storage)
├── Set up Next.js with shadcn/ui
├── Basic auth flow (sign up, log in, Google OAuth)
└── Deploy to Vercel + Cloud Run (CI/CD)

Week 2: Core Upload Flow
├── Create space flow
├── File upload to Supabase storage
├── Background job: PDF → text extraction
├── Background job: Syllabus → knowledge map
└── Display knowledge map (simple list view)

Week 3: Quizzes
├── Quiz generation from topics
├── MCQ quiz interface
├── Response evaluation (Haiku)
├── Basic mastery tracking
└── Progress dashboard (v1)

Week 4: Gap Analysis
├── Graded test upload
├── Gap identification
├── Gap display on dashboard
├── Quiz targeting gaps
└── Polish, bugs, user testing
```

---

## Appendix: Key Technical Snippets

### Supabase Schema (SQL)

```sql
-- Enable pgvector for future embeddings
create extension if not exists vector;

-- Core tables
create table spaces (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    name text not null,
    subject text,
    semester text,
    created_at timestamptz default now(),
    settings jsonb default '{}'::jsonb
);

create table documents (
    id uuid primary key default gen_random_uuid(),
    space_id uuid references spaces(id) on delete cascade,
    type text check (type in ('syllabus', 'material', 'test')),
    original_filename text not null,
    storage_path text not null,
    mime_type text,
    extracted_text text,
    processing_status text default 'pending',
    processed_at timestamptz,
    created_at timestamptz default now(),
    metadata jsonb default '{}'::jsonb
);

create table knowledge_maps (
    id uuid primary key default gen_random_uuid(),
    space_id uuid references spaces(id) on delete cascade,
    document_id uuid references documents(id),
    version int default 1,
    is_active boolean default true,
    created_at timestamptz default now()
);

create table topics (
    id uuid primary key default gen_random_uuid(),
    knowledge_map_id uuid references knowledge_maps(id) on delete cascade,
    parent_topic_id uuid references topics(id),
    name text not null,
    description text,
    sequence_order int,
    estimated_date date,
    is_milestone boolean default false,
    difficulty_level int check (difficulty_level between 1 and 5),
    metadata jsonb default '{}'::jsonb
);

create table topic_mastery (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade,
    topic_id uuid references topics(id) on delete cascade,
    mastery_level int default 0 check (mastery_level between 0 and 100),
    confidence numeric(3,2) default 0,
    last_assessed_at timestamptz,
    assessment_count int default 0,
    is_gap boolean default false,
    gap_priority int,
    unique (user_id, topic_id)
);

-- Row Level Security
alter table spaces enable row level security;
create policy "Users can only see their own spaces"
    on spaces for all using (auth.uid() = user_id);

-- Similar policies for other tables...
```

### FastAPI Auth Middleware

```python
# middleware/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from supabase import create_client
import os

security = HTTPBearer()
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

async def get_current_user(token: str = Depends(security)):
    try:
        user = supabase.auth.get_user(token.credentials)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

### Document Processing Job

```python
# jobs/process_document.py
from anthropic import Anthropic
import fitz  # PyMuPDF

async def process_document(document_id: str):
    # 1. Fetch document metadata
    doc = await db.documents.get(document_id)
    
    # 2. Download file from storage
    file_bytes = await storage.download(doc.storage_path)
    
    # 3. Extract text
    if doc.mime_type == "application/pdf":
        text = extract_pdf_text(file_bytes)
        if not text or len(text) < 100:  # Probably scanned
            text = await extract_with_vision(file_bytes)
    elif doc.mime_type.startswith("image/"):
        text = await extract_with_vision(file_bytes)
    else:
        text = file_bytes.decode("utf-8")
    
    # 4. Update document
    await db.documents.update(document_id, {
        "extracted_text": text,
        "processing_status": "extracted"
    })
    
    # 5. If syllabus, trigger knowledge extraction
    if doc.type == "syllabus":
        await extract_knowledge_map(document_id)

def extract_pdf_text(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

async def extract_with_vision(file_bytes: bytes) -> str:
    client = Anthropic()
    # Use Claude's vision to extract text from images/scanned PDFs
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(file_bytes).decode()}},
                {"type": "text", "text": "Extract all text from this document. Preserve structure and formatting where possible."}
            ]
        }]
    )
    return response.content[0].text
```

---