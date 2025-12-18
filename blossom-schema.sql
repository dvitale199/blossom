-- ============================================================================
-- Blossom.ai Database Schema
-- ============================================================================
-- 
-- Merged schema supporting both v0 MVP and future v1 features.
-- Run this against your Supabase database.
--
-- Prerequisites: Supabase project with auth.users table enabled
--
-- Structure:
--   v0 (build now):  spaces, conversations, messages
--   v1 (build later): user_profiles, quiz_attempts, learning_events
--
-- The v0 tables support the core learning flow.
-- The v1 tables support personalization, analytics, and background processing.
-- All tables are created now so the schema is stable.
-- ============================================================================


-- ============================================================================
-- ENUMS
-- ============================================================================

-- Space context types (v0: just exploratory, expand later)
CREATE TYPE space_context AS ENUM ('exploratory');
-- Future: 'professional', 'academic', 'certification'

-- Message roles
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');


-- ============================================================================
-- V0 TABLES: Core Learning Flow
-- ============================================================================

-- ----------------------------------------------------------------------------
-- SPACES (v0)
-- ----------------------------------------------------------------------------
-- A space is a learning context — a topic the user wants to learn.
-- Contains conversations and will eventually hold knowledge maps, mastery state.

CREATE TABLE IF NOT EXISTS spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Core fields
    name TEXT NOT NULL,                   -- Display name ("Learn Calculus")
    topic TEXT NOT NULL,                  -- Subject matter ("Calculus")
    goal TEXT,                            -- What they want to achieve
    
    -- Type of learning context
    context_type space_context NOT NULL DEFAULT 'exploratory',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Expansion slot for future features
    metadata JSONB DEFAULT '{}'::jsonb
    -- Future metadata: { knowledge_map_id, mastery_summary, last_topic_covered }
);

CREATE INDEX IF NOT EXISTS idx_spaces_user ON spaces(user_id);

-- ----------------------------------------------------------------------------
-- CONVERSATIONS (v0)
-- ----------------------------------------------------------------------------
-- A conversation is a chat session within a space.
-- Users can have multiple conversations per space (different sessions).

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Session tracking
    status TEXT DEFAULT 'active',         -- active, ended, archived
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Future: AI-generated summary for context compression
    summary TEXT,
    
    -- Expansion slot
    metadata JSONB DEFAULT '{}'::jsonb
    -- Future metadata: { topics_covered, quiz_count, duration_minutes, mood }
);

CREATE INDEX IF NOT EXISTS idx_conversations_space ON conversations(space_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(user_id, status);

-- ----------------------------------------------------------------------------
-- MESSAGES (v0)
-- ----------------------------------------------------------------------------
-- Individual messages within a conversation.
-- Quiz data is stored in metadata for v0, extracted to quiz_attempts in v1.

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Core fields
    role message_role NOT NULL,
    content TEXT NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Expansion slot: holds quiz data, topic annotations, etc.
    metadata JSONB DEFAULT '{}'::jsonb
    -- Quiz metadata structure:
    -- {
    --   "type": "quiz",
    --   "quiz_id": "uuid",
    --   "questions": [{ "id", "text", "type", "options", "correct_answer" }],
    --   "status": "pending" | "completed",
    --   "responses": [{ "question_id", "user_answer", "is_correct", "feedback" }],
    --   "completed_at": "timestamp"
    -- }
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(conversation_id, created_at);


-- ============================================================================
-- V1 TABLES: Personalization & Analytics
-- ============================================================================
-- These tables are created now but not used until v1.
-- They support: tutor personalization, background job extraction, analytics.

-- ----------------------------------------------------------------------------
-- USER_PROFILES (v1)
-- ----------------------------------------------------------------------------
-- Stores learning state across all spaces and sessions.
-- The Tutor reads this to personalize responses.
-- The Background Job writes to this after each session.

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    
    -- User-provided information (set during onboarding or in settings)
    display_name TEXT,
    learning_goals TEXT,                  -- Free text: overall learning goals
    self_assessed_background TEXT,        -- Free text: what they already know
    preferences JSONB DEFAULT '{}',       -- { quiz_frequency, session_length, explanation_style }
    
    -- Learning state (updated by Background Job)
    topics JSONB DEFAULT '{}',            -- See structure below
    
    -- Learning style (append-only, updated by Background Job)
    learning_style_observations JSONB DEFAULT '[]',  -- Array of observation strings
    
    -- Session context (updated by Background Job)
    current_topic TEXT,                   -- Suggested focus for next session
    recent_sessions JSONB DEFAULT '[]',   -- Last 3 session summaries (denormalized)
    open_questions JSONB DEFAULT '[]',    -- Unresolved questions to revisit
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_session_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- Topics JSONB structure:
-- {
--   "u-substitution": {
--     "first_seen": "2024-01-15T10:00:00Z",
--     "last_seen": "2024-01-18T15:00:00Z",
--     "sessions_count": 3,
--     "comprehension": 4,           -- 1-5 scale
--     "quiz_scores": [1.0, 0.8],
--     "last_quizzed": "2024-01-18T15:30:00Z",
--     "notes": "Understood mechanics, building intuition"
--   }
-- }
--
-- Comprehension Scale:
-- 1 = No understanding, completely lost
-- 2 = Struggling, needs significant help
-- 3 = Learning, getting it but not solid
-- 4 = Solid, understands well
-- 5 = Mastered, could teach it

-- ----------------------------------------------------------------------------
-- QUIZ_ATTEMPTS (v1)
-- ----------------------------------------------------------------------------
-- Detailed log of quiz questions and answers.
-- v0: Quiz data lives in message.metadata
-- v1: Background Job extracts to this table for analytics and spaced repetition

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    space_id UUID REFERENCES spaces(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    
    -- Quiz data
    topic TEXT NOT NULL,
    question_text TEXT,
    user_answer TEXT,
    correct BOOLEAN,
    attempts INTEGER DEFAULT 1,
    
    -- Context
    confidence_signals JSONB,             -- { hints_needed, hesitation, time_taken }
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_topic ON quiz_attempts(user_id, topic);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_space ON quiz_attempts(space_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_conversation ON quiz_attempts(conversation_id);

-- ----------------------------------------------------------------------------
-- LEARNING_EVENTS (v1)
-- ----------------------------------------------------------------------------
-- Event log for analytics, debugging, and future agent triggers.
-- Captures meaningful moments across all learning activity.

CREATE TABLE IF NOT EXISTS learning_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    space_id UUID REFERENCES spaces(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    
    -- Event data
    event_type TEXT NOT NULL,             -- See catalog below
    payload JSONB NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_user ON learning_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON learning_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_space ON learning_events(space_id);
CREATE INDEX IF NOT EXISTS idx_events_conversation ON learning_events(conversation_id);

-- Event Catalog:
--
-- SESSION LIFECYCLE (Emitter: API)
--   session_started:       { user_id, conversation_id, space_id, timestamp }
--   session_ended:         { user_id, conversation_id, timestamp, duration_minutes, message_count, total_tokens }
--
-- LEARNING EVENTS (Emitter: Background Job)
--   topic_introduced:      { user_id, conversation_id, topic, timestamp }
--   topic_revisited:       { user_id, conversation_id, topic, prior_comprehension, timestamp }
--   quiz_attempted:        { user_id, conversation_id, topic, question_summary, correct, attempts, timestamp }
--   comprehension_updated: { user_id, topic, old_level, new_level, timestamp }
--
-- BEHAVIORAL SIGNALS (Emitter: Background Job)
--   frustration_detected:  { user_id, conversation_id, topic, context, timestamp }
--   struggle_detected:     { user_id, conversation_id, topic, details, timestamp }
--   breakthrough_moment:   { user_id, conversation_id, topic, details, timestamp }
--   practice_requested:    { user_id, conversation_id, topic, timestamp }
--
-- PROFILE EVENTS (Emitter: API/Frontend)
--   profile_updated:       { user_id, fields_updated, timestamp }
--   goal_set:              { user_id, old_goal, new_goal, timestamp }
--   preferences_changed:   { user_id, changes, timestamp }
--
-- SYSTEM EVENTS (Emitter: Background Job)
--   background_job_started:   { conversation_id, user_id, timestamp }
--   background_job_completed: { conversation_id, user_id, duration_ms, success, timestamp }
--   background_job_failed:    { conversation_id, user_id, error, timestamp }


-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER update_spaces_updated_at
    BEFORE UPDATE ON spaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-create user profile when user signs up
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_profiles (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION create_user_profile();


-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE spaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_events ENABLE ROW LEVEL SECURITY;

-- Spaces: Users own their spaces
CREATE POLICY "Users own their spaces"
    ON spaces FOR ALL
    USING (auth.uid() = user_id);

-- Conversations: Users own their conversations
CREATE POLICY "Users own their conversations"
    ON conversations FOR ALL
    USING (auth.uid() = user_id);

-- Messages: Users own messages in their conversations
CREATE POLICY "Users own messages in their conversations"
    ON messages FOR ALL
    USING (
        conversation_id IN (
            SELECT id FROM conversations WHERE user_id = auth.uid()
        )
    );

-- User profiles: Users own their profile
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Quiz attempts: Users own their quiz history
CREATE POLICY "Users own their quiz attempts"
    ON quiz_attempts FOR ALL
    USING (auth.uid() = user_id);

-- Learning events: Users can view their events
CREATE POLICY "Users can view own events"
    ON learning_events FOR SELECT
    USING (auth.uid() = user_id);

-- Note: Background Job needs service_role key to bypass RLS for writes


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get a user's topics sorted by last_seen (for Tutor context limiting)
CREATE OR REPLACE FUNCTION get_recent_topics(p_user_id UUID, p_limit INTEGER DEFAULT 10)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_object_agg(topic_name, topic_data)
    INTO result
    FROM (
        SELECT 
            key AS topic_name,
            value AS topic_data
        FROM user_profiles, jsonb_each(topics)
        WHERE user_id = p_user_id
        ORDER BY (value->>'last_seen')::timestamptz DESC
        LIMIT p_limit
    ) subquery;
    
    RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================================
-- SUMMARY
-- ============================================================================
--
-- v0 Tables (use now):
--   - spaces:        Learning contexts (topic + goal)
--   - conversations: Chat sessions within spaces
--   - messages:      Individual messages, quiz data in metadata
--
-- v1 Tables (created but not used yet):
--   - user_profiles:   Cross-session learning state, tutor personalization
--   - quiz_attempts:   Extracted quiz history for analytics
--   - learning_events: Event log for debugging and future features
--
-- v0 Flow:
--   User creates space → starts conversation → sends messages → tutor responds
--   Quizzes appear inline, stored in message.metadata
--
-- v1 Flow (adds):
--   Background job runs after session_ended
--   Extracts: topics, comprehension, quiz results, learning style
--   Updates: user_profiles, quiz_attempts, learning_events
--   Tutor reads user_profiles for personalization
--
-- ============================================================================