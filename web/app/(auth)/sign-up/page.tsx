import Link from "next/link";

import { AuthForm } from "@/components/auth-form";

export const metadata = { title: "Create account · Draftline" };

export default function SignUpPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Create your account
        </h1>
        <p className="text-sm text-ink-soft">
          Start reviewing AI-drafted replies you stay in control of.
        </p>
      </div>

      <AuthForm mode="sign-up" />

      <p className="text-sm text-ink-soft">
        Already have an account?{" "}
        <Link href="/sign-in" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
