import Link from "next/link";

import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Sign in · Draftline" };

export default function SignInPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Welcome back
        </h1>
        <p className="text-sm text-ink-soft">
          Sign in to review your inbox and drafts.
        </p>
      </div>

      <AuthForm mode="sign-in" />

      <p className="text-sm text-ink-soft">
        New here?{" "}
        <Link href="/sign-up" className="font-medium text-primary underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
