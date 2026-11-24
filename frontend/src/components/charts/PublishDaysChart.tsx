"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtCompact, fmtNumber } from "@/lib/format";

type Row = { day: string; median_views: number; videos: number };

export default function PublishDaysChart({ data }: { data: Row[] }) {
  const best = data.reduce<Row | null>((b, d) => (d.videos >= 3 && (!b || d.median_views > b.median_views) ? d : b), null);
  return (
    <figure>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 16, right: 8, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="var(--color-line)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="day" tick={{ fill: "var(--color-ink-3)", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "var(--color-line)" }} />
          <YAxis tick={{ fill: "var(--color-ink-3)", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v: number) => fmtCompact(v)} width={48} />
          <Tooltip
            cursor={{ fill: "var(--color-surface-2)" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const r = payload[0].payload as Row;
              return (
                <div className="rounded-lg border border-line bg-bg/95 px-3 py-2 text-xs shadow-xl">
                  <p className="font-medium text-ink">{r.day}</p>
                  <p className="text-ink-2">
                    Median <span className="font-semibold text-ink tabular-nums">{fmtNumber(r.median_views)}</span> views
                  </p>
                  <p className="text-ink-3">
                    {r.videos} video{r.videos === 1 ? "" : "s"}
                    {r.videos < 3 && " · too few to compare"}
                  </p>
                </div>
              );
            }}
          />
          <Bar
            dataKey="median_views"
            radius={[4, 4, 0, 0]}
            maxBarSize={36}
            isAnimationActive={false}
            shape={(props: { x?: number; y?: number; width?: number; height?: number; payload?: Row }) => {
              const { x = 0, y = 0, width = 0, height = 0, payload } = props;
              const isBest = payload && best && payload.day === best.day;
              const few = (payload?.videos ?? 0) < 3;
              return (
                <rect
                  x={x}
                  y={y}
                  width={width}
                  height={Math.max(height, 0)}
                  rx={4}
                  fill={isBest ? "var(--color-series-1)" : "var(--color-surface-3)"}
                  opacity={few ? 0.5 : 1}
                />
              );
            }}
          />
        </BarChart>
      </ResponsiveContainer>
      <figcaption className="mt-2 text-xs text-ink-3">
        {best ? (
          <>
            <span className="font-medium text-ink-2">{best.day}</span> has the highest median views. Faded bars have fewer than 3 uploads.
          </>
        ) : (
          "Upload on more days to compare them (3+ videos per day needed)."
        )}
      </figcaption>
    </figure>
  );
}
