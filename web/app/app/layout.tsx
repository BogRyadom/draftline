import { redirect } from "next/navigation";

import { AppNav } from "@/components/app-nav";
import { QueryProvider } from "@/components/query-provider";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/wordmark";
import { createClient } from "@/lib/supabase/server";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // Belt-and-braces: middleware already guards /app, but never render it
  // without a user.
  if (!user) redirect("/sign-in");

  return (
    <QueryProvider>
    <div className="flex min-h-svh flex-col">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3.5 sm:px-6">
          <div className="flex items-center gap-6">
            <Wordmark href="/app" />
            {/* Inline on desktop; a scrollable row below on mobile. */}
            <div className="hidden sm:block">
              <AppNav />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-ink-soft sm:inline">
              {user.email}
            </span>
            <form action="/auth/sign-out" method="post">
              <Button variant="ghost" type="submit" className="h-9 px-3">
                Sign out
              </Button>
            </form>
          </div>
        </div>
        <div className="mx-auto w-full max-w-5xl overflow-x-auto px-4 pb-2 sm:hidden">
          <AppNav />
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 sm:px-6 sm:py-8">
        {children}
      </main>
    </div>
    </QueryProvider>
  );
}
