/** Human-readable labels for audit-log actions, shared by the dashboard and
 *  audit pages. Unknown actions fall back to a title-cased slug. */

export const ACTION_LABELS: Record<string, string> = {
  account_connected: "Connected account",
  sync_run: "Synced inbox",
  email_classified: "Classified email",
  draft_generated: "Generated draft",
  draft_edited: "Edited draft",
  draft_saved_to_gmail: "Saved draft to Gmail",
  draft_dismissed: "Dismissed draft",
  document_uploaded: "Uploaded document",
  document_deleted: "Deleted document",
};

export function actionLabel(action: string): string {
  return (
    ACTION_LABELS[action] ??
    action.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())
  );
}

/** Compact relative time ("just now", "5m ago", "3h ago", "2d ago"), falling
 *  back to an absolute date past a week. */
export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.round((Date.now() - then) / 1000);
  if (diffSec < 45) return "just now";
  const mins = Math.round(diffSec / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
