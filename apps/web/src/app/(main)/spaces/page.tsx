"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { Space } from "@/lib/api";

export default function SpacesPage() {
  const { api, loading: authLoading } = useAuth();
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSpaces() {
      if (!api) return;

      try {
        const data = await api.spaces.list();
        setSpaces(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load spaces");
      } finally {
        setLoading(false);
      }
    }

    if (!authLoading && api) {
      fetchSpaces();
    }
  }, [api, authLoading]);

  if (authLoading || loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-zinc-500">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <Card className="border-red-200 bg-red-50 p-8 text-center dark:border-red-900 dark:bg-red-950">
          <CardHeader>
            <CardTitle className="text-red-700 dark:text-red-400">
              Error loading spaces
            </CardTitle>
            <CardDescription className="text-red-600 dark:text-red-500">
              {error}
            </CardDescription>
          </CardHeader>
          <Button onClick={() => window.location.reload()} className="mt-4">
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Your Spaces</h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            Each space is a learning journey
          </p>
        </div>
        <Button asChild>
          <Link href="/spaces/new">New Space</Link>
        </Button>
      </div>

      {spaces.length === 0 ? (
        <Card className="p-8 text-center">
          <CardHeader>
            <CardTitle>No spaces yet</CardTitle>
            <CardDescription>
              Create your first space to start learning with your AI tutor
            </CardDescription>
          </CardHeader>
          <Button asChild className="mt-4">
            <Link href="/spaces/new">Create Your First Space</Link>
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {spaces.map((space) => (
            <Card
              key={space.id}
              className="cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900"
            >
              <Link href={`/spaces/${space.id}/chat`}>
                <CardHeader>
                  <CardTitle>{space.name}</CardTitle>
                  <CardDescription>{space.topic}</CardDescription>
                </CardHeader>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
