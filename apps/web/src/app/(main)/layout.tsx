export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar - will be implemented later */}
      <aside className="hidden w-64 border-r bg-zinc-50 dark:bg-zinc-950 md:block">
        <div className="p-4">
          <h1 className="text-xl font-bold">Blossom</h1>
        </div>
        <nav className="p-4">
          {/* Space list will go here */}
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1">{children}</main>
    </div>
  );
}
