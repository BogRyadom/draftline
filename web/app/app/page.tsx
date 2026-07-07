import { InboxView } from "@/components/inbox-view";

export default async function InboxPage({
  searchParams,
}: {
  searchParams: Promise<{
    gmail?: string;
    reason?: string;
    category?: string;
    priority?: string;
    sort?: string;
  }>;
}) {
  const params = await searchParams;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Inbox
        </h1>
        <p className="text-sm text-ink-soft">
          Your unread mail, classified and prioritized. Nothing here is ever sent
          for you.
        </p>
      </div>

      <InboxView
        filters={{
          category: params.category,
          priority: params.priority,
          sort: params.sort,
        }}
        gmail={params.gmail}
        reason={params.reason}
      />
    </div>
  );
}
