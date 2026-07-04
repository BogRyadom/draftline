import Link from "next/link";

/** Draftline wordmark: an ink-blue underline mark plus the name in display type. */
export function Wordmark({ href = "/" }: { href?: string }) {
  return (
    <Link
      href={href}
      className="inline-flex items-baseline gap-2 font-display text-lg font-semibold tracking-tight text-ink"
    >
      <span
        aria-hidden
        className="inline-block h-2.5 w-2.5 rounded-[3px] bg-primary"
      />
      Draftline
    </Link>
  );
}
