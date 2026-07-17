import { useState, useCallback, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, FileText, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { brochureApi } from "../api/client";

interface QueuedFile {
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

export default function UploadPage() {
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: (file: File) => brochureApi.upload(file),
  });

  const addFiles = useCallback((files: FileList | null) => {
    if (!files) return;
    const pdfFiles = Array.from(files).filter((f) => f.type === "application/pdf" || f.name.endsWith(".pdf"));
    setQueue((prev) => [...prev, ...pdfFiles.map((file) => ({ file, status: "pending" as const }))]);
  }, []);

  const processQueue = async () => {
    for (let i = 0; i < queue.length; i++) {
      if (queue[i].status !== "pending") continue;
      setQueue((prev) => prev.map((q, idx) => (idx === i ? { ...q, status: "uploading" } : q)));
      try {
        await uploadMutation.mutateAsync(queue[i].file);
        setQueue((prev) => prev.map((q, idx) => (idx === i ? { ...q, status: "done" } : q)));
      } catch (err: any) {
        setQueue((prev) =>
          prev.map((q, idx) =>
            idx === i ? { ...q, status: "error", error: err?.response?.data?.detail || "Upload failed" } : q
          )
        );
      }
    }
    queryClient.invalidateQueries({ queryKey: ["brochures"] });
  };

  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="mb-1 text-2xl font-semibold">Upload Brochure</h1>
      <p className="mb-6 text-sm text-neutral-500">
        Upload one or more car brochure PDFs. DriveWise will parse, chunk, and index them so you can ask questions
        grounded strictly in their content.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition-colors ${
          dragOver
            ? "border-brand-500 bg-brand-50 dark:bg-brand-500/10"
            : "border-neutral-300 dark:border-neutral-700"
        }`}
      >
        <UploadCloud className="mb-3 h-10 w-10 text-brand-500" />
        <p className="font-medium">Drag & drop PDF brochures here</p>
        <p className="text-sm text-neutral-500">or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {queue.length > 0 && (
        <div className="mt-6 space-y-2">
          {queue.map((q, idx) => (
            <div
              key={idx}
              className="flex items-center gap-3 rounded-lg border border-neutral-200 p-3 text-sm dark:border-neutral-800"
            >
              <FileText className="h-4 w-4 shrink-0 text-neutral-400" />
              <span className="flex-1 truncate">{q.file.name}</span>
              {q.status === "pending" && <span className="text-neutral-400">Queued</span>}
              {q.status === "uploading" && <Loader2 className="h-4 w-4 animate-spin text-brand-500" />}
              {q.status === "done" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
              {q.status === "error" && (
                <span className="flex items-center gap-1 text-red-500">
                  <XCircle className="h-4 w-4" /> {q.error}
                </span>
              )}
            </div>
          ))}
          <button
            onClick={processQueue}
            className="mt-2 rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
          >
            Upload {queue.filter((q) => q.status === "pending").length} file(s)
          </button>
        </div>
      )}
    </div>
  );
}
