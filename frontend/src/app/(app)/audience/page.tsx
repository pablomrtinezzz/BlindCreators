"use client";

import Link from "next/link";
import { useDeferredValue, useState } from "react";
import useSWR from "swr";
import { Heart, Search, Sparkles } from "lucide-react";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtNumber } from "@/lib/format";
import type { AudienceInsights, CommentRow } from "@/lib/types";

const DEMAND_TONE: Record<string, "good" | "warn" | "neutral"> = { high: "good", medium: "warn", low: "neutral" };

function Insights() {
  const [data, setData] = useState<AudienceInsights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setData(await api<AudienceInsights>("ai/audience-insights", { method: "POST" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="What your audience wants next"
        subtitle="AI reading of your most-liked comments"
        action={
          <Button variant={data ? "secondary" : "primary"} onClick={() => void run()} loading={loading}>
            {!loading && <Sparkles size={15} aria-hidden />} {data ? "Refresh" : "Analyse comments"}
          </Button>
        }
      />
      <div className="px-5 pb-5 pt-4" aria-live="polite">
        {error && <p className="mb-3 text-sm text-warn">{error}</p>}
        {!data ? (
          <p className="text-sm text-ink-3">Groups recurring requests, lists the questions viewers keep asking and pitches videos with a ready-to-film hook.</p>
        ) : (
          <div className="space-y-6">
            <p className="text-sm leading-relaxed text-ink">{data.summary}</p>
            <section>
              <h3 className="mb-2 text-xs font-medium text-ink-3">Video ideas</h3>
              <ul className="grid gap-3 md:grid-cols-2">
                {data.video_ideas.map((i) => (
                  <li key={i.title} className="rounded-xl border border-line bg-bg p-4">
                    <p className="font-medium text-ink">{i.title}</p>
                    <p className="mt-2 border-l-2 border-brand pl-2 text-sm italic text-ink-2">“{i.hook}”</p>
                    <p className="mt-2 text-xs text-ink-3">{i.why}</p>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h3 className="mb-2 text-xs font-medium text-ink-3">Recurring themes</h3>
              <ul className="space-y-3">
                {data.themes.map((t) => (
                  <li key={t.theme}>
                    <p className="flex items-center gap-2 text-sm font-medium text-ink">
                      {t.theme} <Badge tone={DEMAND_TONE[t.demand.toLowerCase()] ?? "neutral"}>{t.demand} demand</Badge>
                    </p>
                    <ul className="mt-1 space-y-0.5">
                      {t.evidence.map((e, n) => <li key={n} className="text-xs italic text-ink-3">“{e}”</li>)}
                    </ul>
                  </li>
                ))}
              </ul>
            </section>
            {data.open_questions.length > 0 && (
              <section>
                <h3 className="mb-2 text-xs font-medium text-ink-3">Questions viewers keep asking</h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-ink-2">
                  {data.open_questions.map((q) => <li key={q}>{q}</li>)}
                </ul>
              </section>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function TopComments() {
  const [q, setQ] = useState("");
  const query = useDeferredValue(q.trim());
  const { data, error, isLoading } = useSWR<{ total: number; comments: CommentRow[] }>(
    `comments/top?limit=100${query ? `&q=${encodeURIComponent(query)}` : ""}`,
    { keepPreviousData: true },
  );
  return (
    <Card>
      <CardHeader title="Most-liked comments" subtitle={data ? `${fmtNumber(data.total)} comments stored` : undefined} />
      <div className="px-5 pt-3">
        <label className="relative block">
          <span className="sr-only">Search comments</span>
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" aria-hidden />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search comments (e.g. “next”, “tutorial”)"
            className="w-full rounded-lg border border-line bg-bg py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-3 focus:border-brand focus:outline-none"
          />
        </label>
      </div>
      {error ? (
        <ErrorState error={error} />
      ) : isLoading && !data ? (
        <LoadingBlock />
      ) : !data?.comments.length ? (
        <EmptyState title={query ? "No comments match" : "No comments yet"} />
      ) : (
        <ul className="max-h-[70vh] divide-y divide-line overflow-y-auto px-5 pb-3 pt-2">
          {data.comments.map((c) => (
            <li key={c.id} className="py-3">
              <p className="whitespace-pre-line text-sm text-ink">{c.text}</p>
              <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-3">
                <span className="flex items-center gap-1"><Heart size={12} aria-hidden /> {fmtNumber(c.likes)}</span>
                <span>{c.author}</span>
                {c.video_id && (
                  <Link href={`/videos/${c.video_id}?tab=comments`} className="line-clamp-1 text-brand hover:underline">
                    {c.video_title}
                  </Link>
                )}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function AudiencePage() {
  return (
    <>
      <PageHeader title="Audience" description="Your comment section is a backlog of video ideas. Mine it." />
      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3"><Insights /></div>
        <div className="xl:col-span-2"><TopComments /></div>
      </div>
    </>
  );
}
