import { HeaderSkeleton, Skeleton } from "@/components/ui/skeleton";

export default function KnowledgeLoading() {
  return (
    <div className="flex flex-col gap-6">
      <HeaderSkeleton />
      <Skeleton className="h-10 w-56" />
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between gap-4 border-b border-border px-4 py-3 last:border-b-0">
            <div className="flex flex-col gap-1.5">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-3 w-28" />
            </div>
            <Skeleton className="h-5 w-24" />
          </div>
        ))}
      </div>
    </div>
  );
}
