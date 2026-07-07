import { HeaderSkeleton, Skeleton } from "@/components/ui/skeleton";

export default function InboxLoading() {
  return (
    <div className="flex flex-col gap-6">
      <HeaderSkeleton />
      <Skeleton className="h-16 w-full" />
      <div className="flex flex-col gap-2.5">
        <Skeleton className="h-6 w-full max-w-md" />
        <Skeleton className="h-6 w-full max-w-sm" />
      </div>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2 border-b border-border px-4 py-3 last:border-b-0">
            <div className="flex justify-between gap-4">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-4 w-16" />
            </div>
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    </div>
  );
}
