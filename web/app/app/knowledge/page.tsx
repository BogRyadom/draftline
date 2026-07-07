import { AutoRefresh } from "@/components/auto-refresh";
import { DeleteDocumentButton } from "@/components/delete-document-button";
import { UploadDocument } from "@/components/upload-document";
import { apiFetch } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

type DocItem = {
  id: string;
  filename: string;
  mime_type: string | null;
  status: string;
  chunk_count: number;
  created_at: string;
};

export const metadata = { title: "Knowledge · Draftline" };

export default async function KnowledgePage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token ?? "";

  const res = await apiFetch<DocItem[]>("/documents", token);
  const docs = res.ok ? res.data : [];
  const processing = docs.some((d) => d.status === "processing");

  return (
    <div className="flex flex-col gap-6">
      <AutoRefresh active={processing} />

      <div className="flex flex-col gap-1.5">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          Knowledge base
        </h1>
        <p className="max-w-prose text-sm text-ink-soft">
          Upload the documents Draftline should ground its reply drafts in. Each
          file is split into chunks and embedded for retrieval — drafts cite the
          chunks they use.
        </p>
      </div>

      <UploadDocument />

      {!res.ok ? (
        <ErrorCard message={res.error} />
      ) : docs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-surface px-6 py-12 text-center">
          <p className="text-sm font-medium text-ink">No documents yet</p>
          <p className="mt-1 text-sm text-ink-soft">
            Upload a PDF or DOCX to start building your knowledge base.
          </p>
        </div>
      ) : (
        <ul className="overflow-hidden rounded-xl border border-border bg-surface">
          {docs.map((doc) => (
            <DocumentRow key={doc.id} doc={doc} />
          ))}
        </ul>
      )}
    </div>
  );
}

function DocumentRow({ doc }: { doc: DocItem }) {
  return (
    <li className="flex items-center justify-between gap-4 border-b border-border px-4 py-3 last:border-b-0">
      <div className="flex min-w-0 flex-col gap-1">
        <span className="truncate text-sm font-medium text-ink">
          {doc.filename}
        </span>
        <span className="text-xs text-ink-soft">
          Added {formatDate(doc.created_at)}
        </span>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <StatusBadge status={doc.status} chunkCount={doc.chunk_count} />
        <DeleteDocumentButton documentId={doc.id} filename={doc.filename} />
      </div>
    </li>
  );
}

function StatusBadge({
  status,
  chunkCount,
}: {
  status: string;
  chunkCount: number;
}) {
  if (status === "ready") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
        <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-primary" />
        Ready · {chunkCount} chunk{chunkCount === 1 ? "" : "s"}
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="inline-flex items-center rounded-full bg-urgent/10 px-2 py-0.5 text-xs font-medium text-urgent">
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-soft">
      <span aria-hidden className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink-soft" />
      Processing…
    </span>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-urgent/30 bg-urgent/10 px-4 py-3">
      <p className="text-sm font-medium text-urgent">
        Couldn&rsquo;t load your knowledge base
      </p>
      <p className="mt-1 text-sm text-ink-soft">{message}</p>
    </div>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
