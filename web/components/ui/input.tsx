import * as React from "react";

export function Input({
  className = "",
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-ink outline-none placeholder:text-ink-soft/60 focus-visible:border-primary ${className}`}
      {...props}
    />
  );
}
