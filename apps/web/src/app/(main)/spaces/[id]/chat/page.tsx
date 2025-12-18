"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "@/components/chat/chat-message";
import { QuizBlock } from "@/components/chat/quiz-block";
import { useAuth } from "@/hooks/use-auth";
import { Message as ApiMessage, Space } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: {
    type?: string;
    questions?: Array<{
      id: string;
      text: string;
      options: string[];
      correct_answer: string;
    }>;
    status?: string;
    responses?: Array<{
      question_id: string;
      user_answer: string;
      is_correct: boolean;
    }>;
  };
}

function apiMessageToMessage(msg: ApiMessage): Message {
  return {
    id: msg.id,
    role: msg.role as "user" | "assistant",
    content: msg.content,
    metadata: msg.metadata as Message["metadata"],
  };
}

export default function ChatPage() {
  const params = useParams();
  const spaceId = params.id as string;
  const { api, loading: authLoading } = useAuth();

  const [space, setSpace] = useState<Space | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize: load space, get or create conversation, load messages
  const initializeChat = useCallback(async () => {
    if (!api || !spaceId) return;

    try {
      setInitializing(true);
      setError(null);

      // Get space details
      const spaceData = await api.spaces.get(spaceId);
      setSpace(spaceData);

      // Get existing conversations or create one
      const conversations = await api.conversations.list(spaceId);

      let convId: string;
      if (conversations.length > 0) {
        // Use the most recent conversation
        convId = conversations[0].id;
      } else {
        // Create a new conversation
        const newConv = await api.conversations.create(spaceId);
        convId = newConv.id;
      }

      setConversationId(convId);

      // Load messages
      const convWithMessages = await api.conversations.get(convId);
      setMessages(convWithMessages.messages.map(apiMessageToMessage));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to initialize chat");
    } finally {
      setInitializing(false);
    }
  }, [api, spaceId]);

  useEffect(() => {
    if (!authLoading && api) {
      initializeChat();
    }
  }, [authLoading, api, initializeChat]);

  const handleSend = async () => {
    if (!input.trim() || loading || !api || !conversationId) return;

    const userContent = input;
    setInput("");
    setLoading(true);

    // Optimistically add user message
    const tempUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userContent,
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      const response = await api.conversations.sendMessage(conversationId, {
        content: userContent,
      });

      // Replace temp message with real one and add assistant response
      setMessages((prev) => {
        // Remove the temp message
        const filtered = prev.filter((m) => m.id !== tempUserMessage.id);
        // Add the real user message (it's stored on server) and assistant response
        return [
          ...filtered,
          {
            id: `user-${Date.now()}`,
            role: "user" as const,
            content: userContent,
          },
          apiMessageToMessage(response.message),
        ];
      });
    } catch (err) {
      // Remove the temp message and show error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMessage.id));
      setError(err instanceof Error ? err.message : "Failed to send message");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuizSubmit = async (
    messageId: string,
    responses: Array<{ question_id: string; user_answer: string }>
  ) => {
    if (!api) return;

    try {
      const updatedMessage = await api.messages.submitQuizResponse(
        messageId,
        responses
      );

      // Update the message in state with the response
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? apiMessageToMessage(updatedMessage) : m
        )
      );
    } catch (err) {
      console.error("Failed to submit quiz:", err);
    }
  };

  if (authLoading || initializing) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4">
        <p className="text-red-500">{error}</p>
        <Button onClick={() => initializeChat()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="border-b p-4">
        <h1 className="text-lg font-semibold">{space?.name || "Learning Space"}</h1>
        {space?.topic && (
          <p className="text-sm text-zinc-500">{space.topic}</p>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-zinc-500 mt-8">
            <p className="text-lg">Start your learning journey!</p>
            <p className="text-sm mt-2">
              Ask a question or tell me what you&apos;d like to learn about.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id}>
            <ChatMessage
              role={message.role}
              content={message.content}
            />
            {message.metadata?.type === "quiz" && message.metadata.questions && (
              <QuizBlock
                messageId={message.id}
                questions={message.metadata.questions}
                status={message.metadata.status || "pending"}
                responses={message.metadata.responses}
                onSubmit={(responses) => handleQuizSubmit(message.id, responses)}
              />
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-zinc-500">
            <div className="h-2 w-2 rounded-full bg-zinc-400 animate-bounce" />
            <div className="h-2 w-2 rounded-full bg-zinc-400 animate-bounce [animation-delay:0.2s]" />
            <div className="h-2 w-2 rounded-full bg-zinc-400 animate-bounce [animation-delay:0.4s]" />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={loading}
            className="flex-1"
          />
          <Button onClick={handleSend} disabled={loading || !input.trim()}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
