import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, FileText, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { brochureApi } from "../api/client";

export default function LibraryPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["brochures"],
    queryFn: () => brochureApi.list().then((r) => r.data),
    refetchInterval: (query) =>
      query.state.data?.brochures.some((b) => b.status === "processing") ? 3000 : false,
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => brochureApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["brochures"] }),
  });

  return (
    <div className="mx-auto max-w-4xl p-8">
      <h1 className="mb-1 text-2xl font-semibold">Brochure Library</h1>
      <p className="mb-6 text-sm text-neutral-500">Manage the brochures DriveWise can answer questions from.</p>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-neutral-100 dark:bg-neutral-900" />
          ))}
        </div>
      )}

      {data && data.brochures.length === 0 && (
        <div className="rounded-xl border border-dashed border-neutral-300 p-10 text-center text-sm text-neutral-500 dark:border-neutral-700">
          No brochures uploaded yet. Head to Upload to add your first one.
        </div>
      )}

      <div className="space-y-3">
        {data?.brochures.map((b) => (
          <div
            key={b.id}
            className="flex items-center gap-4 rounded-xl border border-neutral-200 p-4 dark:border-neutral-800"
          >
            <FileText className="h-5 w-5 shrink-0 text-brand-500" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{b.car_name || b.file_name}</p>
              <p className="text-xs text-neutral-500">
                {b.manufacturer ? `${b.manufacturer} · ` : ""}
                {b.page_count} pages · {b.file_name}
              </p>
            </div>

            <StatusBadge status={b.status} />

            <button
              onClick={() => removeMutation.mutate(b.id)}
              className="rounded-lg p-2 text-neutral-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950/40"
              title="Delete brochure"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "ready")
    return (
      <span className="flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700 dark:bg-green-900/40 dark:text-green-400">
        <CheckCircle2 className="h-3 w-3" /> Ready
      </span>
    );
  if (status === "failed")
    return (
      <span className="flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 dark:bg-red-900/40 dark:text-red-400">
        <AlertCircle className="h-3 w-3" /> Failed
      </span>
    );
  return (
    <span className="flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
      <Loader2 className="h-3 w-3 animate-spin" /> Processing
    </span>
  );
}
