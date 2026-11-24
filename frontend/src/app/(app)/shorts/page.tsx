"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import HookScatter from "@/components/charts/HookScatter";
import { Badge, Card, CardHeader, EmptyState, ErrorState, LoadingBlock, PageHeader, Stat, Thumb, cx } from "@/components/ui";
import { fmtCompact, fmtNumber, fmtPct, fmtTimestamp } from "@/lib/format";
import type { ShortRow, ShortsLab } from "@/lib/types";

type SortKey = "hook" | "viewed" | "views" | "recent";
const SORTS: { id: SortKey; label: string }[] = [
  { id: "hook", label: "Weakest hook" },
  { id: "viewed", label: "Lowest % viewed" },
  { id: "views", label: "Most views" },
  { id: "recent", label: "Newest" },
];

function sortRows(rows: ShortRow[], key: SortKey) {
  const nullsLast = (v: number | null, dir: 1 | -1) => (v == null ? Infinity : v * dir);
  const copy = [...rows];
  if (key === "hook") copy.sort((a, b) => nullsLast(a.hook_retention_pct, 1) - nullsLast(b.hook_retention_pct, 1));
  if (key === "viewed") copy.sort((a, b) => nullsLast(a.avg_view_pct, 1) - nullsLast(b.avg_view_pct, 1));
  if (key === "views") copy.sort((a, b) => b.views - a.views);
  return copy;
}

export default function ShortsLabPage() {
  const { data, error, isLoading, mutate } = useSWR<ShortsLab>("shorts/lab");
  const [sort, setSort] = useState<SortKey>("hook");
  const rows = useMemo(() => sortRows(data?.shorts ?? [], sort), [data, sort]);

  if (error) return <ErrorState error={error} retry={() => void mutate()} />;
  if (isLoading || !data) return <LoadingBlock />;
  if (!data.shorts.length)
    return (
      <>
        <PageHeader title="Shorts Lab" />
        <Card>
          <EmptyState title="No Shorts found" description="Once your Shorts are synced you'll see hooks, loops and drop-offs here." />
        </Card>
      </>
    );

  const looping = data.shorts.filter((s) => s.looping).length;
  const reliable = data.shorts.filter((s) => s.reliable).length;
  return (
    <>
      <PageHeader
        title="Shorts Lab"
        description={`In the Shorts feed the first ${data.hook_seconds} seconds decide everything. Compare hooks against hold, then open a Short to fix it line by line.`}
      />
      <section aria-label="Shorts benchmarks" className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Median hook" value={fmtPct(data.medians.hook_retention_pct)} hint={`Still watching at ${data.hook_seconds} s`} />
        <Stat label="Median % viewed" value={fmtPct(data.medians.avg_view_pct)} hint="Above 100% means replays" />
        <Stat label="Looping Shorts" value={`${looping}/${data.shorts.length}`} hint="Viewed more than once on average" />
        <Stat label="Reliable curves" value={`${reliable}/${data.shorts.length}`} hint={`${fmtNumber(data.min_views_for_retention)}+ views`} />
      </section>

      <Card className="mb-6">
        <CardHeader title="Hook vs. hold" subtitle="Each dot is a Short (size = views). Dashed lines are channel medians." />
        <div className="px-3 pb-5 pt-2 sm:px-5">
          <HookScatter rows={data.shorts} medianHook={data.medians.hook_retention_pct} medianViewed={data.medians.avg_view_pct} hookSeconds={data.hook_seconds} />
        </div>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader
          title="Every Short, ranked"
          action={
            <label className="flex items-center gap-2 text-xs text-ink-3">
              Sort
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                className="rounded-md border border-line bg-surface-2 px-2 py-1 text-xs text-ink"
              >
                {SORTS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </label>
          }
        />
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-y border-line text-left text-xs text-ink-3">
                <th scope="col" className="px-4 py-2.5 font-medium">Short and opening line</th>
                <th scope="col" className="px-4 py-2.5 text-right font-medium">Hook</th>
                <th scope="col" className="px-4 py-2.5 text-right font-medium">% viewed</th>
                <th scope="col" className="hidden px-4 py-2.5 text-right font-medium md:table-cell">Biggest drop</th>
                <th scope="col" className="px-4 py-2.5 text-right font-medium">Views</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((s) => {
                const weak = data.medians.hook_retention_pct != null && s.hook_retention_pct != null && s.hook_retention_pct < data.medians.hook_retention_pct - 3;
                return (
                  <tr key={s.id} className={cx("group hover:bg-surface-2", !s.reliable && "opacity-70")}>
                    <td className="px-4 py-2.5">
                      <Link href={`/videos/${s.id}?tab=hook`} className="flex items-center gap-3">
                        <Thumb src={s.thumbnail_url} alt="" short />
                        <div className="min-w-0">
                          <p className="line-clamp-1 font-medium text-ink group-hover:text-brand">{s.title}</p>
                          <p className="mt-0.5 line-clamp-1 text-xs italic text-ink-3">{s.first_line ? `“${s.first_line}”` : "No transcript"}</p>
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={cx("tabular-nums", weak ? "font-semibold text-ink" : "text-ink-2")}>{fmtPct(s.hook_retention_pct)}</span>
                      {weak && <Badge tone="warn" className="ml-2">weak</Badge>}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-ink-2">
                      {fmtPct(s.avg_view_pct)} {s.looping && <Badge tone="brand" className="ml-1">loops</Badge>}
                    </td>
                    <td className="hidden px-4 py-2.5 text-right tabular-nums text-ink-3 md:table-cell">
                      {s.biggest_drop_sec != null ? `−${s.biggest_drop_pct}% at ${fmtTimestamp(s.biggest_drop_sec)}` : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-ink">{fmtCompact(s.views)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="px-5 py-3 text-xs text-ink-3">
          Faded rows have fewer than {fmtNumber(data.min_views_for_retention)} views, so their curves are noisy and excluded from medians.
        </p>
      </Card>
    </>
  );
}
