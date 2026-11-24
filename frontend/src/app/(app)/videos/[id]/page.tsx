"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import useSWR from "swr";
import { AlertTriangle, ArrowLeft, ExternalLink, Heart, MessageCircle, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import RetentionChart from "@/components/charts/RetentionChart";
import { Badge, Button, Card, CardHeader, EmptyState, ErrorState, LoadingBlock, Stat, Thumb, cx } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtCompact, fmtDate, fmtDuration, fmtNumber, fmtPct, fmtTimestamp, youtubeUrl } from "@/lib/format";
import type { CommentRow, HookReview, Segment, VideoDetail } from "@/lib/types";

type Tab = "script" | "comments" | "hook";
const TABS: { id: Tab; label: string }[] = [
  { id: "script", label: "Script × Retention" },
  { id: "hook", label: "Hook doctor" },
  { id: "comments", label: "Comments" },
];

function SeverityBadge({ s }: { s: Segment }) {
  if (s.delta_pct == null) return null;
  if (s.severity === "leak")
    return (
      <Badge tone="critical">
        <TrendingDown size={11} aria-hidden /> {s.delta_pct}%
      </Badge>
    );
  if (s.severity === "gain")
    return (
      <Badge tone="good">
        <TrendingUp size={11} aria-hidden /> +{s.delta_pct}%
      </Badge>
    );
  return <span className="text-[11px] tabular-nums text-ink-3">{s.delta_pct}%</span>;
}

function ScriptTab({ d }: { d: VideoDetail }) {
  const [hover, setHover] = useState<Segment | null>(null);
  const hasCurve = d.curve.length > 0;
  const leaks = d.segments.filter((s) => s.severity === "leak").sort((a, b) => (a.delta_pct ?? 0) - (b.delta_pct ?? 0));

  return (
    <div className="grid gap-6 xl:grid-cols-3">
      <div className="space-y-6 xl:col-span-2">
        <Card>
          <CardHeader
            title="Retention curve"
            subtitle={
              d.benchmark_videos > 0
                ? `Compared with the median of ${d.benchmark_videos} other ${d.video.is_short ? "Shorts" : "videos"}`
                : "No comparable videos yet for a channel benchmark"
            }
          />
          <div className="px-3 pb-4 pt-4 sm:px-5">
            {hasCurve ? (
              <RetentionChart curve={d.curve} segments={d.segments} dropOffs={d.drop_offs} highlight={hover} />
            ) : (
              <EmptyState
                title="No retention curve for this video"
                description="YouTube only reports retention once a video has enough views. It will appear after a later sync."
              />
            )}
            {hasCurve && !d.video.reliable && (
              <p className="mt-3 flex items-start gap-2 rounded-lg border border-warn/40 bg-warn/10 p-3 text-xs text-warn">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" aria-hidden />
                Fewer than {fmtNumber(d.min_views_for_retention)} views: this curve is noisy. Treat line-by-line changes as hints, not facts.
              </p>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Script, line by line"
            subtitle={
              d.transcript.status === "ok"
                ? `Change in viewers while each line plays${d.transcript.auto_generated ? " · auto-captions, timing ±1 s" : ""}`
                : "Transcript unavailable"
            }
          />
          {d.segments.length === 0 ? (
            <EmptyState
              title="No script for this video"
              description={
                d.transcript.status === "none"
                  ? "This video has no captions. Enable auto-captions on YouTube and sync again."
                  : "Scripts are fetched during sync."
              }
            />
          ) : (
            <ol className="divide-y divide-line px-2 pb-2 pt-3">
              {d.segments.map((s) => (
                <li
                  key={s.idx}
                  onMouseEnter={() => setHover(s)}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover(s)}
                  onBlur={() => setHover(null)}
                  tabIndex={0}
                  className={cx(
                    "flex items-start gap-3 rounded-lg px-3 py-2.5 outline-none",
                    hover?.idx === s.idx && "bg-surface-2",
                    s.severity === "leak" && "border-l-2 border-critical",
                  )}
                >
                  <a
                    href={youtubeUrl(d.video.id, s.start_sec)}
                    target="_blank"
                    rel="noreferrer"
                    className="w-14 shrink-0 pt-0.5 font-mono text-xs text-ink-3 hover:text-brand"
                    title="Open on YouTube at this moment"
                  >
                    {fmtTimestamp(s.start_sec)}
                  </a>
                  <p className="flex-1 text-sm leading-relaxed text-ink">{s.text}</p>
                  <div className="flex w-24 shrink-0 flex-col items-end gap-0.5">
                    <SeverityBadge s={s} />
                    {s.retention_start_pct != null && (
                      <span className="text-[11px] tabular-nums text-ink-3">
                        {s.retention_start_pct}% → {s.retention_end_pct}%
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader title="Steepest drops" subtitle="After the first 3 seconds, ignoring the end screen" />
          {d.drop_offs.length === 0 ? (
            <p className="px-5 pb-5 pt-3 text-sm text-ink-3">{hasCurve ? "No sharp drops — the curve declines smoothly." : "—"}</p>
          ) : (
            <ul className="space-y-3 px-5 pb-5 pt-3">
              {d.drop_offs.map((x) => (
                <li key={x.at_sec} className="rounded-xl border border-line bg-bg p-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-ink-2">{fmtTimestamp(x.at_sec)}</span>
                    <Badge tone="critical">−{x.drop_pct}% viewers</Badge>
                  </div>
                  {x.line && <p className="mt-2 text-sm italic text-ink">“{x.line}”</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>
        {leaks.length > 0 && (
          <Card>
            <CardHeader title="Lines that leak viewers" subtitle="Losing viewers faster than this video's average" />
            <ul className="space-y-2 px-5 pb-5 pt-3 text-sm">
              {leaks.slice(0, 5).map((s) => (
                <li key={s.idx} className="flex gap-2">
                  <span className="shrink-0 font-mono text-xs leading-5 text-ink-3">{fmtTimestamp(s.start_sec)}</span>
                  <span className="text-ink-2">{s.text}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}

function HookTab({ d }: { d: VideoDetail }) {
  const [review, setReview] = useState<HookReview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      setReview(await api<HookReview>(`ai/videos/${d.video.id}/hook-review`, { method: "POST" }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  const opening = d.segments.slice(0, 3);
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <Card className="p-5 lg:col-span-2">
        <h2 className="text-sm font-semibold text-ink">The opening</h2>
        <p className="mt-1 text-xs text-ink-3">What viewers hear before deciding to stay.</p>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-xl border border-line bg-bg p-3">
            <p className="text-xs text-ink-3">Still watching at 3 s</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-ink">{fmtPct(d.video.hook_retention_pct)}</p>
          </div>
          <div className="rounded-xl border border-line bg-bg p-3">
            <p className="text-xs text-ink-3">Channel median</p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-ink-2">{fmtPct(d.curve.find((p) => p.sec >= 3)?.benchmark)}</p>
          </div>
        </div>
        <blockquote className="mt-4 space-y-1 border-l-2 border-brand pl-3 text-sm italic text-ink">
          {opening.length ? opening.map((s) => <p key={s.idx}>{s.text}</p>) : <p className="text-ink-3">No transcript available.</p>}
        </blockquote>
        <Button variant="primary" className="mt-5 w-full" onClick={() => void run()} loading={loading}>
          {!loading && <Sparkles size={15} aria-hidden />} {review ? "Review again" : "Review this hook"}
        </Button>
        {error && <p className="mt-3 text-sm text-warn">{error}</p>}
      </Card>
      <Card className="p-5 lg:col-span-3">
        {!review ? (
          <EmptyState
            icon={<Sparkles size={20} />}
            title="Get a diagnosis and 3 alternative openings"
            description="Uses this video's opening lines, its retention in the first seconds and your channel's benchmark."
          />
        ) : (
          <div className="space-y-5" aria-live="polite">
            <div>
              <h3 className="text-xs font-medium text-ink-3">Diagnosis</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink">{review.diagnosis}</p>
            </div>
            <div>
              <h3 className="text-xs font-medium text-ink-3">Try instead</h3>
              <ul className="mt-2 space-y-2">
                {review.rewrites.map((r, i) => (
                  <li key={i} className="rounded-xl border border-line bg-bg p-3">
                    <p className="text-sm font-medium text-ink">“{r.hook}”</p>
                    <p className="mt-1 text-xs text-ink-3">{r.technique}</p>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-brand/30 bg-brand/10 p-3">
              <h3 className="text-xs font-medium text-brand">Fix first</h3>
              <p className="mt-1 text-sm text-ink">{review.fix_first}</p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

function CommentsTab({ id }: { id: string }) {
  const { data, error, isLoading } = useSWR<{ comments: CommentRow[]; total: number }>(`videos/${id}/comments?limit=100`);
  if (error) return <ErrorState error={error} />;
  if (isLoading || !data) return <LoadingBlock />;
  if (!data.comments.length) return <Card><EmptyState title="No comments stored for this video" /></Card>;
  return (
    <Card>
      <CardHeader title={`Top comments`} subtitle={`${data.comments.length} most liked of ${fmtNumber(data.total)}`} />
      <ul className="divide-y divide-line px-5 pb-3 pt-2">
        {data.comments.map((c) => (
          <li key={c.id} className="py-3">
            <p className="text-xs font-medium text-ink-2">{c.author}</p>
            <p className="mt-1 whitespace-pre-line text-sm text-ink">{c.text}</p>
            <p className="mt-1.5 flex gap-4 text-xs text-ink-3">
              <span className="flex items-center gap-1"><Heart size={12} aria-hidden /> {fmtNumber(c.likes)}</span>
              {c.reply_count > 0 && <span className="flex items-center gap-1"><MessageCircle size={12} aria-hidden /> {c.reply_count}</span>}
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Workspace() {
  const { id } = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const tab = (TABS.find((t) => t.id === search.get("tab"))?.id ?? "script") as Tab;
  const { data, error, isLoading, mutate } = useSWR<VideoDetail>(`videos/${id}`);

  if (error) return <ErrorState error={error} retry={() => void mutate()} />;
  if (isLoading || !data) return <LoadingBlock label="Loading video…" />;
  const v = data.video;

  return (
    <>
      <Link href="/videos" className="mb-4 inline-flex items-center gap-1 text-sm text-ink-3 hover:text-ink">
        <ArrowLeft size={14} aria-hidden /> Videos
      </Link>
      <header className="mb-6 flex flex-wrap items-start gap-5">
        <Thumb src={v.thumbnail_url} alt="" short={v.is_short} className={v.is_short ? "w-16" : "w-40"} />
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold tracking-tight text-ink">{v.title}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-ink-3">
            {fmtDate(v.published_at)} · {fmtDuration(v.duration_sec)}
            {v.is_short && <Badge>Short</Badge>}
            {v.looping && <Badge tone="brand">Loops</Badge>}
          </p>
        </div>
        <a href={youtubeUrl(v.id)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-sm text-ink-2 hover:text-ink">
          Open on YouTube <ExternalLink size={14} aria-hidden />
        </a>
      </header>

      <section aria-label="Video metrics" className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-5">
        <Stat label="Views" value={fmtCompact(v.views)} hint={v.engaged_views != null ? `${fmtCompact(v.engaged_views)} engaged` : undefined} />
        <Stat label="% viewed" value={fmtPct(v.avg_view_pct)} hint={v.avg_view_duration_s != null ? `${Math.round(v.avg_view_duration_s)} s average` : undefined} />
        <Stat label="Hook (3 s)" value={fmtPct(v.hook_retention_pct)} />
        <Stat label="Subs gained" value={fmtNumber(v.subscribers_gained)} hint={v.subs_per_1k_views != null ? `${v.subs_per_1k_views} per 1k views` : undefined} />
        <Stat label="Engagement" value={fmtPct(v.engagement_rate, 1)} hint="(likes + comments) / views" />
      </section>

      <div role="tablist" aria-label="Video views" className="mb-6 flex gap-1 border-b border-line">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => router.replace(`/videos/${id}${t.id === "script" ? "" : `?tab=${t.id}`}`, { scroll: false })}
            className={cx(
              "-mb-px border-b-2 px-4 py-2.5 text-sm transition-colors",
              tab === t.id ? "border-brand font-medium text-ink" : "border-transparent text-ink-3 hover:text-ink",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "script" && <ScriptTab d={data} />}
      {tab === "hook" && <HookTab d={data} />}
      {tab === "comments" && <CommentsTab id={id} />}
    </>
  );
}

export default function VideoPage() {
  return (
    <Suspense fallback={<LoadingBlock />}>
      <Workspace />
    </Suspense>
  );
}
