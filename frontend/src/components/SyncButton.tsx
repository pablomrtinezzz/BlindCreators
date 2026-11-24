"use client";

import { useEffect, useRef, useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { CheckCircle2, CircleAlert, Loader2, RefreshCw, X } from "lucide-react";
import { api } from "@/lib/api";
import type { SyncJob } from "@/lib/types";
import { Button, cx } from "./ui";

const PHASE_LABEL: Record<string, string> = {
  queued: "Queued",
  channel: "Channel",
  videos: "Videos",
  analytics: "Analytics",
  retention: "Retention curves",
  transcripts: "Scripts",
  comments: "Comments",
  thumbnails: "Thumbnails",
  index: "AI search index",
  complete: "Complete",
};

const isActive = (j?: SyncJob | null) => j?.status === "pending" || j?.status === "running";

export function useSync() {
  const { mutate } = useSWRConfig();
  const latest = useSWR<{ job: SyncJob | null }>("sync/jobs/latest", {
    refreshInterval: (d) => (isActive(d?.job) ? 1500 : 0),
  });
  const job = latest.data?.job ?? null;
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wasActive = useRef(false);

  useEffect(() => {
    if (wasActive.current && job && !isActive(job)) {
      // Sync just finished: refresh every cached view.
      void mutate((key) => typeof key === "string" && !key.startsWith("sync/"));
    }
    wasActive.current = isActive(job);
  }, [job, mutate]);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      const created = await api<SyncJob>("sync", { method: "POST" });
      await latest.mutate({ job: created }, { revalidate: false });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the sync");
    } finally {
      setStarting(false);
    }
  }

  return { job, active: isActive(job), starting, error, start, clearError: () => setError(null) };
}

export function SyncProgress({ job }: { job: SyncJob }) {
  const steps = job.phases;
  const current = job.phase_index ?? (job.status === "done" ? steps.length : -1);
  const pct = job.total ? Math.round((job.done / job.total) * 100) : 0;
  return (
    <div aria-live="polite">
      <ol className="space-y-1.5">
        {steps.map((s, i) => {
          const state = job.status === "done" || i < current ? "done" : i === current ? "active" : "todo";
          return (
            <li key={s} className="flex items-center gap-2.5 text-sm">
              {state === "done" ? (
                <CheckCircle2 size={15} className="text-good-ink" aria-label="done" />
              ) : state === "active" && isActive(job) ? (
                <Loader2 size={15} className="animate-spin text-brand" aria-label="in progress" />
              ) : (
                <span className="mx-[3px] h-2 w-2 rounded-full bg-surface-3" aria-hidden />
              )}
              <span className={cx(state === "todo" ? "text-ink-3" : "text-ink")}>{PHASE_LABEL[s] ?? s}</span>
              {state === "active" && isActive(job) && job.total > 1 && (
                <span className="ml-auto text-xs tabular-nums text-ink-3">
                  {job.done}/{job.total}
                </span>
              )}
            </li>
          );
        })}
      </ol>
      {isActive(job) && job.total > 1 && (
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface-3">
          <div className="h-full bg-brand transition-all" style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}

export default function SyncButton() {
  const { job, active, starting, error, start, clearError } = useSync();
  const [open, setOpen] = useState(false);
  const failed = job && ["failed", "partial", "interrupted"].includes(job.status);

  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <Button variant="primary" onClick={() => (active ? setOpen(true) : void start().then(() => setOpen(true)))} loading={starting}>
          {!starting && <RefreshCw size={15} className={active ? "animate-spin" : ""} aria-hidden />}
          {active ? `Syncing · ${PHASE_LABEL[job!.phase] ?? job!.phase}` : "Sync channel"}
        </Button>
        {(job || error) && (
          <Button variant="ghost" className="px-2" aria-label="Sync details" onClick={() => setOpen((o) => !o)}>
            {failed || error ? <CircleAlert size={16} className="text-warn" /> : <CheckCircle2 size={16} className="text-ink-3" />}
          </Button>
        )}
      </div>

      {open && (
        <div className="absolute right-0 top-12 z-40 w-80 rounded-xl border border-line bg-surface p-4 shadow-2xl shadow-black/50">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-ink">Channel sync</p>
            <button className="rounded p-1 text-ink-3 hover:text-ink" onClick={() => { setOpen(false); clearError(); }} aria-label="Close">
              <X size={15} />
            </button>
          </div>
          {error && <p className="mb-3 rounded-lg border border-warn/40 bg-warn/10 p-2.5 text-xs text-warn">{error}</p>}
          {job ? (
            <>
              <SyncProgress job={job} />
              {job.message && <p className="mt-3 text-xs text-ink-2">{job.message}</p>}
              {!active && (
                <p className="mt-3 text-xs text-ink-3">
                  Only new or changed data is fetched, so re-running is fast and resumes interrupted syncs.
                </p>
              )}
            </>
          ) : (
            !error && <p className="text-sm text-ink-3">No sync yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
