import { redirect } from "next/navigation";

import { AppNav } from "@/components/app-nav";
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
    <div className="flex min-h-svh flex-col">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-6 py-3.5">
          <div className="flex items-center gap-6">
            <Wordmark href="/app" />
            <AppNav />
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
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">
        {children}
      </main>
    </div>
  );
}
