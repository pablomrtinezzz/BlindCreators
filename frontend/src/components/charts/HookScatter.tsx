"use client";

import { useRouter } from "next/navigation";
import { CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import type { ShortRow } from "@/lib/types";
import { fmtCompact } from "@/lib/format";

type Point = { x: number; y: number; z: number; row: ShortRow };

export default function HookScatter({
  rows,
  medianHook,
  medianViewed,
  hookSeconds,
}: {
  rows: ShortRow[];
  medianHook: number | null;
  medianViewed: number | null;
  hookSeconds: number;
}) {
  const router = useRouter();
  const data: Point[] = rows
    .filter((r) => r.reliable && r.hook_retention_pct != null && r.avg_view_pct != null)
    .map((r) => ({ x: r.hook_retention_pct!, y: r.avg_view_pct!, z: r.views, row: r }));

  if (data.length < 3) {
    return <p className="py-10 text-center text-sm text-ink-3">Needs at least 3 Shorts with enough views to plot.</p>;
  }

  return (
    <figure>
      <ResponsiveContainer width="100%" height={320}>
        <ScatterChart margin={{ top: 16, right: 16, bottom: 20, left: -4 }}>
          <CartesianGrid stroke="var(--color-line)" strokeDasharray="2 4" />
          <XAxis
            type="number"
            dataKey="x"
            name="Hook"
            domain={["dataMin - 5", "dataMax + 5"]}
            tick={{ fill: "var(--color-ink-3)", fontSize: 11 }}
            tickFormatter={(v: number) => `${Math.round(v)}%`}
            label={{ value: `Still watching at ${hookSeconds}s`, position: "insideBottom", offset: -12, fill: "var(--color-ink-3)", fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Viewed"
            domain={["dataMin - 5", "dataMax + 5"]}
            tick={{ fill: "var(--color-ink-3)", fontSize: 11 }}
            tickFormatter={(v: number) => `${Math.round(v)}%`}
            width={48}
          />
          <ZAxis type="number" dataKey="z" range={[60, 260]} />
          {medianHook != null && <ReferenceLine x={medianHook} stroke="var(--color-benchmark)" strokeDasharray="4 4" />}
          {medianViewed != null && <ReferenceLine y={medianViewed} stroke="var(--color-benchmark)" strokeDasharray="4 4" />}
          <Tooltip
            cursor={false}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload as Point;
              return (
                <div className="max-w-64 rounded-lg border border-line bg-bg/95 px-3 py-2 text-xs shadow-xl">
                  <p className="font-medium text-ink">{p.row.title}</p>
                  <p className="mt-1 text-ink-2">
                    Hook {p.x}% · Viewed {p.y}% · {fmtCompact(p.row.views)} views
                  </p>
                  <p className="mt-1 text-ink-3">Click to open</p>
                </div>
              );
            }}
          />
          <Scatter
            data={data}
            fill="var(--color-series-1)"
            fillOpacity={0.85}
            stroke="var(--color-surface)"
            strokeWidth={2}
            isAnimationActive={false}
            onClick={(p: unknown) => {
              const row = (p as { payload?: Point })?.payload?.row;
              if (row) router.push(`/videos/${row.id}`);
            }}
            className="cursor-pointer"
          />
        </ScatterChart>
      </ResponsiveContainer>
      <figcaption className="mt-1 grid grid-cols-2 gap-2 text-[11px] text-ink-3">
        <span>↖ Weak hook, strong hold — fix the first seconds</span>
        <span className="text-right">↗ Winners — study and repeat</span>
        <span>↙ Weak hook and hold — rethink the idea</span>
        <span className="text-right">↘ Great hook, weak middle — tighten pacing</span>
      </figcaption>
    </figure>
  );
}
