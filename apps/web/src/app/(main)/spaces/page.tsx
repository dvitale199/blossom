import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Link from "next/link";

export default function SpacesPage() {
  // TODO: Fetch spaces from API
  const spaces: { id: string; name: string; topic: string }[] = [];

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
            <Card key={space.id} className="cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900">
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
