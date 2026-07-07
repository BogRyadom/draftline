import { AuditView } from "@/components/audit-view";

export const metadata = { title: "Audit log · Draftline" };

export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<{ action?: string; page?: string }>;
}) {
  const params = await searchParams;
  const action = params.action;
  const page = Math.max(0, Number.parseInt(params.page ?? "0", 10) || 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Audit log
        </h1>
        <p className="text-sm text-ink-soft">
          A complete, timestamped record of what Draftline did — every connect,
          sync, classification, draft, and save.
        </p>
      </div>

      <AuditView action={action} page={page} />
    </div>
  );
}
