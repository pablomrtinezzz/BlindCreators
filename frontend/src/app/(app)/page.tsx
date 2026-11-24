"use client";

import Link from "next/link";
import useSWR from "swr";
import { ArrowRight, CalendarDays, CheckCircle2, MessagesSquare, RefreshCw, Zap } from "lucide-react";
import PublishDaysChart from "@/components/charts/PublishDaysChart";
import { useSync, SyncProgress } from "@/components/SyncButton";
import { Badge, Button, Card, CardHeader, ErrorState, PageHeader, Skeleton, Stat, Thumb } from "@/components/ui";
import { fmtCompact, fmtNumber, fmtPct, fmtRelative } from "@/lib/format";
import type { Dashboard, DashboardAction } from "@/lib/types";

const ACTION_META: Record<DashboardAction["kind"], { icon: typeof Zap; label: string; cta: string }> = {
  weak_hook: { icon: Zap, label: "Weakest recent hook", cta: "Open hook doctor" },
  best_day: { icon: CalendarDays, label: "Best day to publish", cta: "See all videos" },
  conversation: { icon: MessagesSquare, label: "Biggest conversation", cta: "Read the comments" },
};

function ActionCard({ a }: { a: DashboardAction }) {
  const meta = ACTION_META[a.kind];
  const href = a.kind === "best_day" ? "/videos" : a.kind === "conversation" ? `/videos/${a.video_id}?tab=comments` : `/videos/${a.video_id}?tab=hook`;
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-center gap-2 text-xs font-medium text-ink-3">
        <meta.icon size={14} className="text-brand" aria-hidden /> {meta.label}
      </div>
      <p className="mt-3 line-clamp-2 font-medium text-ink">{a.title}</p>
      <p className="mt-1 flex-1 text-sm text-ink-2">{a.message}</p>
      <Link href={href} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand hover:underline">
        {meta.cta} <ArrowRight size={14} aria-hidden />
      </Link>
    </Card>
  );
}

function Onboarding() {
  const { job, active, start, starting, error } = useSync();
  return (
    <Card className="mx-auto max-w-2xl p-8">
      <h2 className="text-xl font-semibold text-ink">Let&apos;s read your channel</h2>
      <p className="mt-2 text-sm text-ink-2">
        The first sync pulls your videos, retention curves, scripts and comments. It takes a few minutes; you can keep browsing meanwhile.
      </p>
      <ol className="mt-6 space-y-3 text-sm">
        <li className="flex items-center gap-3 text-ink">
          <CheckCircle2 size={18} className="text-good-ink" aria-hidden /> Google account connected (read-only)
        </li>
        <li className="flex items-center gap-3 text-ink">
          <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full border border-line text-[10px] text-ink-3">2</span>
          Sync your channel
        </li>
        <li className="flex items-center gap-3 text-ink-3">
          <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full border border-line text-[10px]">3</span>
          Find your weakest hook and fix it in the next upload
        </li>
      </ol>
      <div className="mt-8">
        {job && (active || job.status !== "done") ? (
          <div className="rounded-xl border border-line bg-bg p-4">
            <SyncProgress job={job} />
            {job.message && <p className="mt-3 text-xs text-ink-2">{job.message}</p>}
          </div>
        ) : null}
        {!active && (
          <Button variant="primary" className="mt-4" onClick={() => void start()} loading={starting}>
            <RefreshCw size={15} aria-hidden /> {job ? "Run sync again" : "Start first sync"}
          </Button>
        )}
        {error && <p className="mt-3 text-sm text-warn">{error}</p>}
      </div>
    </Card>
  );
}

export default function OverviewPage() {
  const { data, error, isLoading, mutate } = useSWR<Dashboard>("dashboard");

  if (error) return <ErrorState error={error} retry={() => void mutate()} />;
  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-72" />
        <div className="grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-40" />)}
        </div>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
          {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      </div>
    );
  }
  if (data.kpis.videos === 0) return <Onboarding />;

  const k = data.kpis;
  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            {data.channel.thumbnail && (
              // eslint-disable-next-line @next/next/no-img-element -- channel avatar
              <img src={data.channel.thumbnail} alt="" className="h-9 w-9 rounded-full" referrerPolicy="no-referrer" />
            )}
            {data.channel.title ?? "Your channel"}
          </span>
        }
        description={
          <>
            {fmtNumber(data.channel.subscribers)} subscribers · synced {fmtRelative(data.channel.last_synced_at)}
          </>
        }
      />

      {data.actions.length > 0 && (
        <section aria-label="What to do next" className="mb-6 grid gap-4 md:grid-cols-3">
          {data.actions.map((a) => <ActionCard key={a.kind} a={a} />)}
        </section>
      )}

      <section aria-label="Key metrics" className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Stat label="Videos" value={fmtNumber(k.videos)} hint={`${k.shorts} Shorts · ${k.uploads_last_28d} in last 28 days`} />
        <Stat label="Median views" value={fmtCompact(k.median_views)} hint={`${fmtCompact(k.total_views)} total`} />
        <Stat label="Median % viewed" value={fmtPct(k.median_avg_view_pct)} hint="Average view percentage" />
        <Stat label="Median hook" value={fmtPct(k.median_hook_retention_pct)} hint="Still watching at 3 s" />
        <Stat label="Subs per 1k views" value={k.median_subs_per_1k_views ?? "—"} hint="Median per video" />
      </section>

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader title="Median views by publish day" subtitle="Medians resist one viral outlier" />
          <div className="px-5 pb-5 pt-3">
            <PublishDaysChart data={data.publish_days} />
          </div>
        </Card>
        <Card className="lg:col-span-3">
          <CardHeader title="Top videos" subtitle="By lifetime views" action={<Link href="/videos" className="text-xs font-medium text-brand hover:underline">All videos</Link>} />
          <ul className="divide-y divide-line px-2 pb-2 pt-3">
            {data.top_videos.map((v, i) => (
              <li key={v.id}>
                <Link href={`/videos/${v.id}`} className="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-surface-2">
                  <span className="w-4 text-xs tabular-nums text-ink-3">{i + 1}</span>
                  <Thumb src={v.thumbnail_url} alt="" short={v.is_short} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{v.title}</p>
                    <p className="text-xs text-ink-3">
                      {fmtPct(v.avg_view_pct)} viewed · hook {fmtPct(v.hook_retention_pct)}
                    </p>
                  </div>
                  {v.looping && <Badge tone="brand">Loops</Badge>}
                  <span className="text-sm font-semibold tabular-nums text-ink">{fmtCompact(v.views)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
