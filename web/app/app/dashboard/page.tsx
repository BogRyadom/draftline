import { DashboardView } from "@/components/dashboard-view";

export const metadata = { title: "Dashboard · Draftline" };

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Dashboard
        </h1>
        <p className="text-sm text-ink-soft">
          Everything Draftline has processed for you — at a glance, from real activity.
        </p>
      </div>

      <DashboardView />
    </div>
  );
}
