const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/**
 * Create an authenticated API client.
 * Pass the Supabase session access token.
 */
export function createAuthenticatedApi(token: string) {
  return {
    // Health check (no auth needed)
    health: () => fetchAPI<{ status: string }>("/health"),

    // Spaces
    spaces: {
      list: () => fetchAPI<Space[]>("/api/spaces", {}, token),
      get: (id: string) => fetchAPI<Space>(`/api/spaces/${id}`, {}, token),
      create: (data: CreateSpaceRequest) =>
        fetchAPI<Space>(
          "/api/spaces",
          {
            method: "POST",
            body: JSON.stringify(data),
          },
          token
        ),
    },

    // Conversations
    conversations: {
      list: (spaceId: string) =>
        fetchAPI<Conversation[]>(`/api/spaces/${spaceId}/conversations`, {}, token),
      get: (id: string) =>
        fetchAPI<ConversationWithMessages>(`/api/conversations/${id}`, {}, token),
      create: (spaceId: string) =>
        fetchAPI<Conversation>(
          `/api/spaces/${spaceId}/conversations`,
          { method: "POST" },
          token
        ),
      sendMessage: (conversationId: string, data: { content: string }) =>
        fetchAPI<MessageResponse>(
          `/api/conversations/${conversationId}/messages`,
          {
            method: "POST",
            body: JSON.stringify(data),
          },
          token
        ),
    },

    // Quiz responses
    messages: {
      submitQuizResponse: (
        messageId: string,
        responses: Array<{ question_id: string; user_answer: string }>
      ) =>
        fetchAPI<Message>(
          `/api/messages/${messageId}/quiz-response`,
          {
            method: "POST",
            body: JSON.stringify({ responses }),
          },
          token
        ),
    },
  };
}

// Unauthenticated API (for health checks, etc.)
export const api = {
  health: () => fetchAPI<{ status: string }>("/health"),
};

// Types
export interface Space {
  id: string;
  name: string;
  topic: string;
  goal: string | null;
  created_at: string;
}

export interface CreateSpaceRequest {
  name: string;
  topic: string;
  goal?: string;
}

export interface Conversation {
  id: string;
  space_id: string;
  started_at: string;
  last_message_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface MessageResponse {
  message: Message;
  has_quiz: boolean;
}
