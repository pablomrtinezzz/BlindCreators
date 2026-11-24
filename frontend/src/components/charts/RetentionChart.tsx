"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { CurvePoint, DropOff, Segment } from "@/lib/types";
import { fmtTimestamp } from "@/lib/format";

const AXIS = { fill: "var(--color-ink-3)", fontSize: 11 };

export default function RetentionChart({
  curve,
  segments,
  dropOffs,
  highlight,
  height = 300,
}: {
  curve: CurvePoint[];
  segments: Segment[];
  dropOffs: DropOff[];
  highlight: Segment | null;
  height?: number;
}) {
  const hasBenchmark = curve.some((p) => p.benchmark != null);
  const maxY = Math.max(100, ...curve.map((p) => Math.max(p.y, p.benchmark ?? 0)));
  const lineAt = (sec: number) => segments.find((s) => s.start_sec <= sec && sec <= s.end_sec)?.text;

  return (
    <figure>
      <div className="mb-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-ink-2" aria-hidden>
        <span className="flex items-center gap-2">
          <span className="h-0.5 w-5 rounded bg-series-1" /> This video
        </span>
        {hasBenchmark && (
          <span className="flex items-center gap-2">
            <span className="w-5 border-t-2 border-dashed border-benchmark" /> Channel median
          </span>
        )}
        {dropOffs.length > 0 && (
          <span className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full border-2 border-surface bg-critical" /> Steepest drops
          </span>
        )}
      </div>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={curve} margin={{ top: 8, right: 12, bottom: 4, left: -8 }}>
          <CartesianGrid stroke="var(--color-line)" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="sec"
            type="number"
            domain={[0, "dataMax"]}
            tick={AXIS}
            tickLine={false}
            axisLine={{ stroke: "var(--color-line)" }}
            tickFormatter={(v: number) => `${Math.round(v)}s`}
          />
          <YAxis
            domain={[0, Math.ceil(maxY / 10) * 10]}
            tick={AXIS}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${v}%`}
            width={44}
          />
          {highlight && (
            <ReferenceArea x1={highlight.start_sec} x2={highlight.end_sec} fill="var(--color-brand)" fillOpacity={0.12} stroke="none" />
          )}
          <Tooltip
            cursor={{ stroke: "var(--color-ink-3)", strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const p = payload[0].payload as CurvePoint;
              const line = lineAt(p.sec);
              return (
                <div className="max-w-64 rounded-lg border border-line bg-bg/95 px-3 py-2 text-xs shadow-xl">
                  <p className="font-mono text-ink-3">{fmtTimestamp(p.sec)}</p>
                  <p className="mt-1 text-ink">
                    <span className="font-semibold tabular-nums">{p.y}%</span> still watching
                  </p>
                  {p.benchmark != null && <p className="text-ink-2">Channel median: {p.benchmark}%</p>}
                  {line && <p className="mt-1.5 border-t border-line pt-1.5 italic text-ink-2">“{line}”</p>}
                </div>
              );
            }}
          />
          {hasBenchmark && (
            <Line dataKey="benchmark" stroke="var(--color-benchmark)" strokeWidth={1.5} strokeDasharray="5 4" dot={false} activeDot={false} isAnimationActive={false} />
          )}
          <Line
            dataKey="y"
            stroke="var(--color-series-1)"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, stroke: "var(--color-surface)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
          {dropOffs.map((d) => (
            <ReferenceDot
              key={d.at_sec}
              x={d.at_sec}
              y={(d.from_pct + d.to_pct) / 2}
              r={5}
              fill="var(--color-critical)"
              stroke="var(--color-surface)"
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <figcaption className="sr-only">
        Audience retention over time.{" "}
        {dropOffs.map((d) => `Drop of ${d.drop_pct}% at ${d.at_sec} seconds.`).join(" ")}
      </figcaption>
    </figure>
  );
}
