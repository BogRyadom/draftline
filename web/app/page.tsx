import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/wordmark";

export default function Landing() {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-6">
        <Wordmark />
        <nav className="flex items-center gap-2">
          <Link href="/sign-in">
            <Button variant="ghost" className="h-9 px-3">
              Sign in
            </Button>
          </Link>
          <Link href="/sign-up">
            <Button className="h-9 px-4">Get started</Button>
          </Link>
        </nav>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-6">
        {/* Hero */}
        <section className="flex flex-col items-start gap-6 py-16 sm:py-24">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-ink-soft">
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-primary" />
            Human-in-the-loop email, never auto-sent
          </span>

          <h1 className="max-w-3xl font-display text-4xl font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
            A calm workspace for a busy inbox.
          </h1>

          <p className="max-w-xl text-lg text-ink-soft">
            Draftline reads your incoming mail, classifies and prioritizes it,
            and writes grounded reply drafts from your own knowledge base — with
            citations. You review, edit, and decide.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <Link href="/sign-up">
              <Button className="h-11 px-5 text-base">Get started</Button>
            </Link>
            <Link href="/sign-in">
              <Button variant="outline" className="h-11 px-5 text-base">
                Sign in
              </Button>
            </Link>
          </div>
        </section>

        {/* Feature triplet */}
        <section className="grid gap-4 pb-20 sm:grid-cols-3">
          <Feature
            title="Classify & prioritize"
            body="Every message gets a category, a priority, and a one-line reason — automatically."
          />
          <Feature
            title="Grounded drafts"
            body="Replies are written from your uploaded documents and cite the exact chunks they used."
          />
          <Feature
            title="You stay in control"
            body="Drafts are saved to Gmail for your review only. There is no send button — ever."
          />
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-1 px-6 py-6 text-xs text-ink-soft">
          <span>Draftline — AI inbox assistant.</span>
          <span>Next.js · FastAPI · Supabase/pgvector · Groq · Gemini.</span>
        </div>
      </footer>
    </div>
  );
}

function Feature({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h3 className="text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-sm text-ink-soft">{body}</p>
    </div>
  );
}
