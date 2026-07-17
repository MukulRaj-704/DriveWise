import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { Send, Car, Sparkles } from "lucide-react";
import { chatApi, ChatMessageOut, SourceAttribution } from "../api/client";
import SourceCards from "../components/SourceCards";
import ConversationSidebar from "../components/ConversationSidebar";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  sources?: SourceAttribution[];
}

const SUGGESTED_QUESTIONS = [
  "What safety features does this car have?",
  "What is the fuel efficiency (mileage)?",
  "What are the available color options?",
  "What is the boot space / cargo capacity?",
];

export default function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: sessionDetail } = useQuery({
    queryKey: ["chat-session", sessionId],
    queryFn: () => chatApi.session(sessionId!).then((r) => r.data),
    enabled: !!sessionId,
  });

  useEffect(() => {
    if (sessionDetail) {
      setMessages(
        sessionDetail.messages.map((m: ChatMessageOut) => ({
          role: m.role,
          content: m.content,
          sources: m.sources || [],
        }))
      );
    }
  }, [sessionDetail]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const askMutation = useMutation({
    mutationFn: (message: string) => chatApi.ask({ message, session_id: sessionId || undefined }),
    onSuccess: (res) => {
      setSessionId(res.data.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: res.data.answer, sources: res.data.sources }]);
      queryClient.invalidateQueries({ queryKey: ["chat-history"] });
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong while generating a response. Please try again." },
      ]);
    },
  });

  const send = (text: string) => {
    const message = text.trim();
    if (!message || askMutation.isPending) return;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    askMutation.mutate(message);
  };

  const startNew = () => {
    setSessionId(null);
    setMessages([]);
  };

  return (
    <div className="flex h-full">
      <ConversationSidebar activeSessionId={sessionId} onSelect={setSessionId} onNew={startNew} />

      <div className="flex flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 && (
            <div className="mx-auto flex h-full max-w-lg flex-col items-center justify-center text-center">
              <Car className="mb-4 h-10 w-10 text-brand-500" />
              <h2 className="text-lg font-semibold">Ask about your car brochures</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Answers are grounded strictly in the brochures you've uploaded — with page-level citations.
              </p>
              <div className="mt-6 grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2 text-left text-sm hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                  >
                    <Sparkles className="h-3.5 w-3.5 shrink-0 text-brand-500" />
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mx-auto max-w-2xl space-y-6">
            {messages.map((m, idx) => (
              <div key={idx} className={m.role === "user" ? "text-right" : "text-left"}>
                <div
                  className={
                    m.role === "user"
                      ? "inline-block rounded-2xl bg-brand-500 px-4 py-2 text-sm text-white"
                      : "inline-block rounded-2xl bg-neutral-100 px-4 py-2 text-sm dark:bg-neutral-900"
                  }
                >
                  <ReactMarkdown
                    components={{
                      code: ({ children }) => (
                        <code className="rounded bg-black/10 px-1 py-0.5 text-xs dark:bg-white/10">{children}</code>
                      ),
                    }}
                  >
                    {m.content}
                  </ReactMarkdown>
                </div>
                {m.role === "assistant" && m.sources && <SourceCards sources={m.sources} />}
              </div>
            ))}

            {askMutation.isPending && (
              <div className="text-left">
                <div className="inline-flex items-center gap-1 rounded-2xl bg-neutral-100 px-4 py-3 dark:bg-neutral-900">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400 [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-neutral-400" />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        <div className="border-t border-neutral-200 p-4 dark:border-neutral-800">
          <div className="mx-auto flex max-w-2xl items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              placeholder="Ask about mileage, safety, variants, pricing..."
              className="flex-1 rounded-full border border-neutral-300 bg-transparent px-4 py-2.5 text-sm outline-none focus:border-brand-500 dark:border-neutral-700"
            />
            <button
              onClick={() => send(input)}
              disabled={askMutation.isPending}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-60"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
