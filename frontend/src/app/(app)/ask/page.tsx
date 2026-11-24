"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowUp, FileText, MessagesSquare } from "lucide-react";
import { Button, Card, PageHeader, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtTimestamp } from "@/lib/format";
import type { AskSource } from "@/lib/types";

type Msg = { role: "user" | "assistant"; text: string; sources?: AskSource[]; error?: boolean };

const EXAMPLES = [
  "What do viewers complain about most?",
  "Which topics did I cover that got the most questions?",
  "How do I usually open my best videos?",
];

export default function AskPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [messages, loading]);

  async function send(question: string) {
    const q = question.trim();
    if (q.length < 3 || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await api<{ answer: string; sources: AskSource[] }>("ai/ask", { method: "POST", body: { question: q } });
      setMessages((m) => [...m, { role: "assistant", text: res.answer, sources: res.sources }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: e instanceof Error ? e.message : "Failed", error: true }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <PageHeader title="Ask your channel" description="Answers grounded in your own scripts and viewer comments, with sources." />
      <Card className="flex min-h-0 flex-1 flex-col">
        <div className="flex-1 space-y-5 overflow-y-auto p-5" aria-live="polite">
          {messages.length === 0 && (
            <div className="mx-auto max-w-lg py-10 text-center">
              <MessagesSquare size={22} className="mx-auto text-ink-3" aria-hidden />
              <p className="mt-3 text-sm text-ink-2">Try one of these:</p>
              <div className="mt-4 flex flex-col gap-2">
                {EXAMPLES.map((e) => (
                  <button key={e} onClick={() => void send(e)} className="rounded-lg border border-line bg-bg px-4 py-2.5 text-left text-sm text-ink-2 hover:border-brand/50 hover:text-ink">
                    {e}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={cx("flex", m.role === "user" && "justify-end")}>
              <div
                className={cx(
                  "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                  m.role === "user" ? "bg-brand text-brand-ink" : m.error ? "border border-warn/40 bg-warn/10 text-warn" : "border border-line bg-bg text-ink",
                )}
              >
                <p className="whitespace-pre-line">{m.text}</p>
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 border-t border-line pt-3">
                    <p className="mb-2 text-xs text-ink-3">Sources</p>
                    <ul className="space-y-1.5">
                      {m.sources.map((s, n) => (
                        <li key={n}>
                          <Link
                            href={`/videos/${s.video_id}${s.type === "comments" ? "?tab=comments" : ""}`}
                            className="flex items-start gap-2 rounded-md p-1 text-xs hover:bg-surface-2"
                          >
                            {s.type === "comments" ? <MessagesSquare size={13} className="mt-0.5 shrink-0 text-ink-3" aria-hidden /> : <FileText size={13} className="mt-0.5 shrink-0 text-ink-3" aria-hidden />}
                            <span className="min-w-0">
                              <span className="font-medium text-ink-2">{s.title}</span>
                              {s.type === "transcript" && <span className="text-ink-3"> · {fmtTimestamp(s.start_sec)}</span>}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-1.5 px-2" role="status" aria-label="Thinking">
              {[0, 1, 2].map((n) => <span key={n} className="h-2 w-2 animate-pulse rounded-full bg-ink-3" style={{ animationDelay: `${n * 150}ms` }} />)}
            </div>
          )}
          <div ref={end} />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void send(input);
          }}
          className="flex items-end gap-2 border-t border-line p-3"
        >
          <label htmlFor="q" className="sr-only">Your question</label>
          <textarea
            id="q"
            rows={1}
            value={input}
            maxLength={1000}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(input);
              }
            }}
            placeholder="Ask anything about your videos and audience…"
            className="max-h-40 min-h-[42px] flex-1 resize-none rounded-lg border border-line bg-bg px-3 py-2.5 text-sm text-ink placeholder:text-ink-3 focus:border-brand focus:outline-none"
          />
          <Button type="submit" variant="primary" className="h-[42px] w-[42px] p-0" disabled={input.trim().length < 3 || loading} aria-label="Send">
            <ArrowUp size={18} />
          </Button>
        </form>
      </Card>
    </div>
  );
}
