/** Placeholder block for loading states. `animate-pulse` is quieted by the
 *  reduced-motion rule in globals.css. */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={`animate-pulse rounded-md bg-surface-2 ${className}`}
    />
  );
}

/** A page header skeleton (title + subtitle), shared by loading views. */
export function HeaderSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      <Skeleton className="h-7 w-48" />
      <Skeleton className="h-4 w-80 max-w-full" />
    </div>
  );
}
