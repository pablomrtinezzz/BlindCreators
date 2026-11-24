"use client";

import { signOut } from "next-auth/react";
import { useState } from "react";
import useSWR, { useSWRConfig } from "swr";
import { LogOut, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { SyncProgress, useSync } from "@/components/SyncButton";
import { Badge, Button, Card, CardHeader, ErrorState, LoadingBlock, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtNumber, fmtRelative } from "@/lib/format";
import type { Me } from "@/lib/types";

const STATUS_TONE = { done: "good", partial: "warn", failed: "critical", interrupted: "warn", running: "brand", pending: "brand" } as const;

function DangerZone() {
  const { mutate } = useSWRConfig();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function wipe() {
    setBusy(true);
    try {
      await api("me/data", { method: "DELETE" });
      setMsg("All stored data was deleted.");
      setConfirm(false);
      await mutate(() => true);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="border-critical/30">
      <CardHeader title="Delete my data" subtitle="Removes every synced video, retention curve, script, comment and search index. Your YouTube channel is not touched." />
      <div className="flex flex-wrap items-center gap-3 px-5 pb-5 pt-4">
        {!confirm ? (
          <Button variant="danger" onClick={() => setConfirm(true)}>
            <Trash2 size={15} aria-hidden /> Delete stored data
          </Button>
        ) : (
          <>
            <span className="text-sm text-ink-2">This can&apos;t be undone.</span>
            <Button variant="danger" onClick={() => void wipe()} loading={busy}>Yes, delete everything</Button>
            <Button variant="ghost" onClick={() => setConfirm(false)}>Cancel</Button>
          </>
        )}
        {msg && <p role="status" className="w-full text-sm text-ink-2">{msg}</p>}
      </div>
    </Card>
  );
}

export default function SettingsPage() {
  const { data, error, isLoading, mutate } = useSWR<Me>("me");
  const { job, active, start, starting, error: syncError } = useSync();

  if (error) return <ErrorState error={error} retry={() => void mutate()} />;
  if (isLoading || !data) return <LoadingBlock />;

  return (
    <div className="max-w-3xl">
      <PageHeader title="Settings" />
      <div className="space-y-6">
        <Card>
          <CardHeader title="Account" />
          <dl className="grid gap-4 px-5 pb-5 pt-4 text-sm sm:grid-cols-2">
            <div><dt className="text-xs text-ink-3">Signed in as</dt><dd className="mt-0.5 text-ink">{data.email}</dd></div>
            <div><dt className="text-xs text-ink-3">YouTube channel</dt><dd className="mt-0.5 text-ink">{data.channel.title ?? "Not synced yet"}</dd></div>
            <div><dt className="text-xs text-ink-3">Subscribers</dt><dd className="mt-0.5 text-ink">{fmtNumber(data.channel.subscribers)}</dd></div>
            <div><dt className="text-xs text-ink-3">Videos stored</dt><dd className="mt-0.5 text-ink">{fmtNumber(data.videos)}</dd></div>
          </dl>
          <div className="flex items-start gap-2 border-t border-line px-5 py-4 text-xs text-ink-3">
            <ShieldCheck size={15} className="shrink-0 text-good-ink" aria-hidden />
            Read-only Google access (YouTube + YouTube Analytics). Tokens stay on the server and are never stored in the database.
          </div>
          <div className="border-t border-line px-5 py-4">
            <Button variant="secondary" onClick={() => void signOut({ callbackUrl: "/login" })}>
              <LogOut size={15} aria-hidden /> Sign out
            </Button>
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Sync"
            subtitle={`Last successful sync ${fmtRelative(data.last_synced_at)}`}
            action={job && <Badge tone={STATUS_TONE[job.status]}>{job.status}</Badge>}
          />
          <div className="px-5 pb-5 pt-4">
            {job && <SyncProgress job={job} />}
            {job?.message && <p className="mt-3 text-sm text-ink-2">{job.message}</p>}
            {job && Object.keys(job.stats).length > 0 && (
              <details className="mt-4 text-xs text-ink-3">
                <summary className="cursor-pointer text-ink-2">Details of the last run</summary>
                <dl className="mt-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
                  {Object.entries(job.stats).map(([phase, counts]) => (
                    <div key={phase} className="flex justify-between gap-2">
                      <dt>{phase}</dt>
                      <dd className="text-right tabular-nums">{Object.entries(counts).map(([k, v]) => `${k}: ${v}`).join(" · ")}</dd>
                    </div>
                  ))}
                </dl>
              </details>
            )}
            <Button variant="primary" className="mt-5" onClick={() => void start()} loading={starting} disabled={active}>
              {!starting && <RefreshCw size={15} aria-hidden />} {active ? "Sync in progress" : "Sync now"}
            </Button>
            {syncError && <p className="mt-3 text-sm text-warn">{syncError}</p>}
          </div>
        </Card>

        <DangerZone />
      </div>
    </div>
  );
}
