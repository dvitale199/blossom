"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";

export default function NewSpacePage() {
  const router = useRouter();
  const { api, loading: authLoading } = useAuth();
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!api) {
      setError("Not authenticated");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const space = await api.spaces.create({
        name,
        topic,
        goal: goal || undefined,
      });
      // Redirect to the new space's chat page
      router.push(`/spaces/${space.id}/chat`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create space");
      setLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center p-8">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Create a New Space</CardTitle>
          <CardDescription>
            A space is a learning journey around a specific topic
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                Space Name
              </label>
              <Input
                id="name"
                placeholder="e.g., Learning Python"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="topic" className="text-sm font-medium">
                What do you want to learn?
              </label>
              <Input
                id="topic"
                placeholder="e.g., Python programming fundamentals"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="goal" className="text-sm font-medium">
                Your goal (optional)
              </label>
              <Input
                id="goal"
                placeholder="e.g., Be able to build a web scraper"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
              />
            </div>

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}

            <div className="flex gap-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={loading || !name || !topic}>
                {loading ? "Creating..." : "Create Space"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
