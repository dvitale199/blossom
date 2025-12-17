-- Blossom.ai v0 Database Schema
-- Run this in Supabase SQL Editor

-- Enums
CREATE TYPE space_context AS ENUM ('exploratory');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system');

-- Spaces: a learning context
CREATE TABLE spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

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
    space_id UUID REFERENCES spaces(id) ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

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
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE NOT NULL,

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
CREATE INDEX idx_spaces_updated ON spaces(user_id, updated_at DESC);
CREATE INDEX idx_conversations_space ON conversations(space_id);
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_last_message ON conversations(space_id, last_message_at DESC);
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

-- Updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to spaces
CREATE TRIGGER update_spaces_updated_at
    BEFORE UPDATE ON spaces
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
