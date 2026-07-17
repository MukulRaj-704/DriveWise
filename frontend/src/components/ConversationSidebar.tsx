import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import { chatApi } from "../api/client";
import clsx from "clsx";

export default function ConversationSidebar({
  activeSessionId,
  onSelect,
  onNew,
}: {
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}) {
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["chat-history"],
    queryFn: () => chatApi.history().then((r) => r.data),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => chatApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["chat-history"] }),
  });

  return (
    <div className="flex w-72 flex-col border-r border-neutral-200 dark:border-neutral-800">
      <div className="p-3">
        <button
          onClick={onNew}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-neutral-300 py-2 text-sm font-medium hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
        >
          <Plus className="h-4 w-4" /> New conversation
        </button>
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto px-3 pb-3">
        {data?.sessions.map((s) => (
          <div
            key={s.id}
            className={clsx(
              "group flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-sm",
              activeSessionId === s.id
                ? "bg-brand-500 text-white"
                : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-300 dark:hover:bg-neutral-900"
            )}
            onClick={() => onSelect(s.id)}
          >
            <MessageSquare className="h-4 w-4 shrink-0" />
            <span className="flex-1 truncate">{s.title}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                removeMutation.mutate(s.id);
              }}
              className="hidden shrink-0 group-hover:block"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
