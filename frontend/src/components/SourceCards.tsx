import { FileText } from "lucide-react";
import { SourceAttribution } from "../api/client";

export default function SourceCards({ sources }: { sources: SourceAttribution[] }) {
  if (!sources.length) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {sources.map((s, idx) => (
        <div
          key={idx}
          className="flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs dark:border-neutral-800 dark:bg-neutral-900"
        >
          <FileText className="h-3.5 w-3.5 text-brand-500" />
          <span className="font-medium">{s.brochure_name}</span>
          {s.section && <span className="text-neutral-400">· {s.section}</span>}
          {s.page != null && <span className="text-neutral-400">· Page {s.page}</span>}
        </div>
      ))}
    </div>
  );
}
