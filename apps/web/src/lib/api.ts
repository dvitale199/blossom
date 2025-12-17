const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Health check
  health: () => fetchAPI<{ status: string }>("/health"),

  // Spaces
  spaces: {
    list: () => fetchAPI<Space[]>("/api/spaces"),
    get: (id: string) => fetchAPI<Space>(`/api/spaces/${id}`),
    create: (data: CreateSpaceRequest) =>
      fetchAPI<Space>("/api/spaces", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Conversations
  conversations: {
    list: (spaceId: string) =>
      fetchAPI<Conversation[]>(`/api/spaces/${spaceId}/conversations`),
    get: (id: string) => fetchAPI<ConversationWithMessages>(`/api/conversations/${id}`),
    create: (spaceId: string) =>
      fetchAPI<Conversation>(`/api/spaces/${spaceId}/conversations`, {
        method: "POST",
      }),
    sendMessage: (conversationId: string, data: { content: string }) =>
      fetchAPI<MessageResponse>(`/api/conversations/${conversationId}/messages`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
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
