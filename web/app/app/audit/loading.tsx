import { HeaderSkeleton, Skeleton } from "@/components/ui/skeleton";

export default function AuditLoading() {
  return (
    <div className="flex flex-col gap-6">
      <HeaderSkeleton />
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-6 w-24" />
        ))}
      </div>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between gap-4 border-b border-border px-4 py-3 last:border-b-0">
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-24" />
            </div>
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}
