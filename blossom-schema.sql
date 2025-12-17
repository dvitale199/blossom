-- Blossom AI Learning Platform: Database Schema
-- Run this against your Supabase database to set up all tables
-- 
-- Prerequisites: Supabase project with auth.users table enabled

-- ============================================================================
-- USER PROFILES
-- ============================================================================
-- Stores learning state, goals, preferences, and session context for each user.
-- The Tutor reads from this at the start of each conversation.
-- The Background Job writes to this after each session.

CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
  
  -- User-provided information (set during onboarding or in settings)
  display_name TEXT,
  learning_goals TEXT,                    -- Free text: what they want to learn
  self_assessed_background TEXT,          -- Free text: what they already know
  preferences JSONB DEFAULT '{}',         -- {quiz_frequency, session_length, explanation_style, etc.}
  
  -- Learning state (updated by Background Job)
  topics JSONB DEFAULT '{}',              -- See structure below
  
  -- Learning style (append-only, updated by Background Job)
  learning_style_observations JSONB DEFAULT '[]',  -- Array of observation strings
  
  -- Session context (updated by Background Job)
  current_topic TEXT,                     -- Suggested focus for next session
  recent_sessions JSONB DEFAULT '[]',     -- Last 3 session summaries (denormalized)
  open_questions JSONB DEFAULT '[]',      -- Unresolved questions to revisit
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_session_at TIMESTAMPTZ
);

-- Index for fast lookup by user
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Topics JSONB structure example:
-- {
--   "u-substitution": {
--     "first_seen": "2024-01-15T10:00:00Z",
--     "last_seen": "2024-01-18T15:00:00Z",
--     "sessions_count": 3,
--     "comprehension": 4,           -- 1-5 scale
--     "quiz_scores": [1.0, 0.8],    -- Array of scores (1.0 = correct, 0.0 = incorrect)
--     "last_quizzed": "2024-01-18T15:30:00Z",
--     "notes": "Understood mechanics, building intuition for when to apply"
--   }
-- }
--
-- Comprehension Scale:
-- 1 = No understanding, completely lost
-- 2 = Struggling, needs significant help
-- 3 = Learning, getting it but not solid
-- 4 = Solid, understands well
-- 5 = Mastered, could teach it


-- ============================================================================
-- QUIZ ATTEMPTS
-- ============================================================================
-- Detailed log of every quiz question asked and answered.
-- Used for analytics and spaced repetition (future feature).
-- Background Job writes to this after extracting quiz moments from transcripts.

CREATE TABLE IF NOT EXISTS quiz_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  session_id UUID,                        -- Links to conversation/session
  topic TEXT NOT NULL,                    -- Topic being tested
  question_text TEXT,                     -- The question asked
  user_answer TEXT,                       -- What the user answered
  correct BOOLEAN,                        -- Did they get it right?
  attempts INTEGER DEFAULT 1,             -- How many tries before correct
  confidence_signals JSONB,               -- Optional: hints needed, hesitation, etc.
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user ON quiz_attempts(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_topic ON quiz_attempts(user_id, topic);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_session ON quiz_attempts(session_id);


-- ============================================================================
-- LEARNING EVENTS
-- ============================================================================
-- Event log for analytics, debugging, and future agent triggers.
-- Captures meaningful moments, not raw activity.
-- Primarily written by the Background Job, some by Tutor endpoint.

CREATE TABLE IF NOT EXISTS learning_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  session_id UUID,                        -- Links to conversation/session
  event_type TEXT NOT NULL,               -- See event catalog below
  payload JSONB NOT NULL,                 -- Event-specific data
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_user ON learning_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON learning_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session ON learning_events(session_id);

-- Event Catalog:
--
-- SESSION LIFECYCLE (Emitter: Tutor Endpoint)
--   session_started:    {user_id, session_id, timestamp}
--   session_ended:      {user_id, session_id, timestamp, duration_minutes, message_count, total_tokens}
--
-- LEARNING EVENTS (Emitter: Background Job)
--   topic_introduced:   {user_id, session_id, topic, timestamp}
--   topic_revisited:    {user_id, session_id, topic, prior_comprehension, timestamp}
--   quiz_attempted:     {user_id, session_id, topic, question_summary, correct, attempts, timestamp}
--   comprehension_updated: {user_id, topic, old_level, new_level, timestamp}
--
-- BEHAVIORAL SIGNALS (Emitter: Background Job)
--   frustration_detected:  {user_id, session_id, topic, context, timestamp}
--   struggle_detected:     {user_id, session_id, topic, details, timestamp}
--   breakthrough_moment:   {user_id, session_id, topic, details, timestamp}
--   practice_requested:    {user_id, session_id, topic, timestamp}
--
-- PROFILE EVENTS (Emitter: API/Frontend)
--   profile_updated:    {user_id, fields_updated, timestamp}
--   goal_set:           {user_id, old_goal, new_goal, timestamp}
--   preferences_changed: {user_id, changes, timestamp}
--
-- SYSTEM EVENTS (Emitter: Background Job)
--   background_job_started:   {session_id, user_id, timestamp}
--   background_job_completed: {session_id, user_id, duration_ms, success, timestamp}
--   background_job_failed:    {session_id, user_id, error, timestamp}


-- ============================================================================
-- CONVERSATIONS (Optional - if not using Supabase Realtime or external storage)
-- ============================================================================
-- Stores chat transcripts. You may already have this or use a different approach.
-- Included here for completeness.

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT,                             -- Auto-generated or user-set
  messages JSONB DEFAULT '[]',            -- Array of {role, content, timestamp}
  status TEXT DEFAULT 'active',           -- active, ended, archived
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(user_id, status);

CREATE OR REPLACE TRIGGER update_conversations_updated_at
  BEFORE UPDATE ON conversations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Messages JSONB structure:
-- [
--   {"role": "user", "content": "Can you explain derivatives?", "timestamp": "2024-01-18T15:00:00Z"},
--   {"role": "assistant", "content": "Sure! Let's start with...", "timestamp": "2024-01-18T15:00:05Z"}
-- ]


-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- Enable RLS so users can only access their own data.
-- Adjust policies based on your auth setup.

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Policies: Users can only access their own rows
CREATE POLICY "Users can view own profile" ON user_profiles
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" ON user_profiles
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile" ON user_profiles
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own quiz attempts" ON quiz_attempts
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own events" ON learning_events
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can view own conversations" ON conversations
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations" ON conversations
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations" ON conversations
  FOR UPDATE USING (auth.uid() = user_id);

-- Note: Background Job needs service role key to bypass RLS for writes
-- Use supabase.auth.admin or service_role key in your backend


-- ============================================================================
-- HELPER FUNCTIONS (Optional)
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
      key as topic_name,
      value as topic_data
    FROM user_profiles, jsonb_each(topics)
    WHERE user_id = p_user_id
    ORDER BY (value->>'last_seen')::timestamptz DESC
    LIMIT p_limit
  ) subquery;
  
  RETURN COALESCE(result, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create profile for new user (call on signup)
CREATE OR REPLACE FUNCTION create_user_profile()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO user_profiles (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Auto-create profile when user signs up
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION create_user_profile();