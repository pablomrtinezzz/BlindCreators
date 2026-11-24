"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { AlertCircle, Search } from "lucide-react";
import { Badge, Card, EmptyState, ErrorState, LoadingBlock, PageHeader, Thumb, cx } from "@/components/ui";
import { fmtCompact, fmtDate, fmtDuration, fmtPct } from "@/lib/format";
import type { Medians, VideoSummary } from "@/lib/types";

type Kind = "all" | "short" | "long";
const KINDS: { id: Kind; label: string }[] = [
  { id: "all", label: "All" },
  { id: "short", label: "Shorts" },
  { id: "long", label: "Long-form" },
];

function HookCell({ value, median }: { value: number | null; median: number | null }) {
  if (value == null) return <span className="text-ink-3">—</span>;
  const below = median != null && value < median - 3;
  return (
    <span className="flex items-center justify-end gap-2">
      <span className="hidden h-1.5 w-16 overflow-hidden rounded-full bg-surface-3 sm:block" aria-hidden>
        <span className={cx("block h-full rounded-full", below ? "bg-series-2" : "bg-series-1")} style={{ width: `${Math.min(value, 100)}%` }} />
      </span>
      <span className={cx("tabular-nums", below ? "text-ink" : "text-ink-2")}>{fmtPct(value)}</span>
    </span>
  );
}

export default function VideosPage() {
  const [kind, setKind] = useState<Kind>("all");
  const [q, setQ] = useState("");
  const { data, error, isLoading, mutate } = useSWR<{ videos: VideoSummary[]; medians: Medians }>(`videos?kind=${kind}`);
  const rows = useMemo(
    () => (data?.videos ?? []).filter((v) => v.title.toLowerCase().includes(q.trim().toLowerCase())),
    [data, q],
  );

  return (
    <>
      <PageHeader title="Videos" description="Every upload with the metrics that predict growth. Open one to see its script against the retention curve." />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div role="tablist" aria-label="Video type" className="flex rounded-lg border border-line bg-surface p-0.5">
          {KINDS.map((k) => (
            <button
              key={k.id}
              role="tab"
              aria-selected={kind === k.id}
              onClick={() => setKind(k.id)}
              className={cx("rounded-md px-3 py-1.5 text-sm", kind === k.id ? "bg-surface-3 font-medium text-ink" : "text-ink-2 hover:text-ink")}
            >
              {k.label}
            </button>
          ))}
        </div>
        <label className="relative ml-auto w-full sm:w-72">
          <span className="sr-only">Search videos</span>
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" aria-hidden />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search titles"
            className="w-full rounded-lg border border-line bg-surface py-2 pl-9 pr-3 text-sm text-ink placeholder:text-ink-3 focus:border-brand focus:outline-none"
          />
        </label>
      </div>

      <Card className="overflow-hidden">
        {error ? (
          <ErrorState error={error} retry={() => void mutate()} />
        ) : isLoading ? (
          <LoadingBlock />
        ) : rows.length === 0 ? (
          <EmptyState title={q ? "No videos match your search" : "No videos yet"} description={q ? undefined : "Run a sync to import your channel."} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-xs text-ink-3">
                  <th scope="col" className="px-4 py-3 font-medium">Video</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">Views</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">% viewed</th>
                  <th scope="col" className="px-4 py-3 text-right font-medium">Hook (3 s)</th>
                  <th scope="col" className="hidden px-4 py-3 text-right font-medium md:table-cell">Subs / 1k</th>
                  <th scope="col" className="hidden px-4 py-3 text-right font-medium lg:table-cell">Published</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((v) => (
                  <tr key={v.id} className="group hover:bg-surface-2">
                    <td className="px-4 py-2.5">
                      <Link href={`/videos/${v.id}`} className="flex items-center gap-3">
                        <Thumb src={v.thumbnail_url} alt="" short={v.is_short} />
                        <div className="min-w-0">
                          <p className="line-clamp-1 font-medium text-ink group-hover:text-brand">{v.title}</p>
                          <p className="mt-0.5 flex items-center gap-2 text-xs text-ink-3">
                            {fmtDuration(v.duration_sec)}
                            {v.is_short && <Badge>Short</Badge>}
                            {v.looping && <Badge tone="brand">Loops</Badge>}
                            {v.has_retention && !v.reliable && (
                              <span className="flex items-center gap-1" title="Too few views for a stable retention curve">
                                <AlertCircle size={12} aria-hidden /> low data
                              </span>
                            )}
                          </p>
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-ink">{fmtCompact(v.views)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-ink-2">{fmtPct(v.avg_view_pct)}</td>
                    <td className="px-4 py-2.5 text-right">
                      <HookCell value={v.hook_retention_pct} median={data?.medians.hook_retention_pct ?? null} />
                    </td>
                    <td className="hidden px-4 py-2.5 text-right tabular-nums text-ink-2 md:table-cell">{v.subs_per_1k_views ?? "—"}</td>
                    <td className="hidden px-4 py-2.5 text-right text-ink-3 lg:table-cell">{fmtDate(v.published_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {data && (
        <p className="mt-3 text-xs text-ink-3">
          Orange hook bars are more than 3 points below the channel median ({fmtPct(data.medians.hook_retention_pct)}).
        </p>
      )}
    </>
  );
}
