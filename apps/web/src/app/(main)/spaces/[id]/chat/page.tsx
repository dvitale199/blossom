"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "@/components/chat/chat-message";
import { QuizBlock } from "@/components/chat/quiz-block";

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

export default function ChatPage() {
  const params = useParams();
  const spaceId = params.id as string;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // TODO: Call API to send message
      // For now, simulate a response
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `I received your message about "${input}". This is a placeholder response. Once connected to the backend, I'll be your AI tutor helping you learn about ${spaceId}!`,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Failed to send message:", error);
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
    // TODO: Submit quiz responses to API
    console.log("Quiz submitted:", messageId, responses);
  };

  return (
    <div className="flex h-screen flex-col">
      {/* Header */}
      <header className="border-b p-4">
        <h1 className="text-lg font-semibold">Learning Space</h1>
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
