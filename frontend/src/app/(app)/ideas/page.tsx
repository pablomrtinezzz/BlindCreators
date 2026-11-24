"use client";

import { useState } from "react";
import { Check, Copy, Sparkles } from "lucide-react";
import { Button, Card, CardHeader, EmptyState, PageHeader, cx } from "@/components/ui";
import { api } from "@/lib/api";

type Ideas = { ideas: { title: string; angle: string }[] };

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => void navigator.clipboard.writeText(text).then(() => { setDone(true); setTimeout(() => setDone(false), 1500); })}
      className="rounded-md p-1.5 text-ink-3 hover:bg-surface-2 hover:text-ink"
      aria-label={done ? "Copied" : "Copy title"}
    >
      {done ? <Check size={15} className="text-good-ink" /> : <Copy size={15} />}
    </button>
  );
}

export default function IdeasPage() {
  const [topic, setTopic] = useState("");
  const [prefs, setPrefs] = useState("");
  const [short, setShort] = useState(true);
  const [data, setData] = useState<Ideas | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setData(await api<Ideas>("ai/titles", { method: "POST", body: { topic, preferences: prefs || null, short } }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  const input = "w-full rounded-lg border border-line bg-bg px-3 py-2.5 text-sm text-ink placeholder:text-ink-3 focus:border-brand focus:outline-none";
  return (
    <>
      <PageHeader title="Ideas" description="Titles modelled on what already works on your channel, not on generic SEO advice." />
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="p-5 lg:col-span-2">
          <form onSubmit={(e) => void submit(e)} className="space-y-4">
            <div>
              <label htmlFor="topic" className="text-xs font-medium text-ink-2">What is the next video about?</label>
              <textarea id="topic" required minLength={2} maxLength={300} rows={3} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. The fastest way to beat the final boss without leveling" className={cx(input, "mt-1.5 resize-none")} />
            </div>
            <div>
              <label htmlFor="prefs" className="text-xs font-medium text-ink-2">Style notes (optional)</label>
              <input id="prefs" maxLength={400} value={prefs} onChange={(e) => setPrefs(e.target.value)} placeholder="e.g. no clickbait, include a number" className={cx(input, "mt-1.5")} />
            </div>
            <fieldset>
              <legend className="text-xs font-medium text-ink-2">Format</legend>
              <div className="mt-1.5 flex rounded-lg border border-line bg-bg p-0.5">
                {[{ v: true, l: "Short" }, { v: false, l: "Long-form" }].map((o) => (
                  <button type="button" key={o.l} aria-pressed={short === o.v} onClick={() => setShort(o.v)} className={cx("flex-1 rounded-md py-1.5 text-sm", short === o.v ? "bg-surface-3 font-medium text-ink" : "text-ink-3")}>
                    {o.l}
                  </button>
                ))}
              </div>
            </fieldset>
            <Button type="submit" variant="primary" className="w-full" loading={loading} disabled={topic.trim().length < 2}>
              {!loading && <Sparkles size={15} aria-hidden />} Generate titles
            </Button>
            {error && <p className="text-sm text-warn">{error}</p>}
          </form>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader title="Suggestions" subtitle="Based on your 12 best-performing uploads of the same format" />
          {!data ? (
            <EmptyState icon={<Sparkles size={20} />} title="Describe your next video" description="You'll get 5 titles in your channel's proven style." />
          ) : (
            <ul className="space-y-2 px-5 pb-5 pt-3" aria-live="polite">
              {data.ideas.map((i) => (
                <li key={i.title} className="flex items-start gap-3 rounded-xl border border-line bg-bg p-4">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-ink">{i.title}</p>
                    <p className="mt-1 text-xs text-ink-3">{i.angle} · {i.title.length} chars</p>
                  </div>
                  <CopyButton text={i.title} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
