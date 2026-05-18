'use client';

import { useEffect, useState, useCallback } from 'react';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface JobStatus {
    job_id: string;
    status: 'pending' | 'running' | 'done' | 'failed';
    phase: string;
    phase_label: string;
    videos_total: number;
    videos_done: number;
    progress: number;
    error: string | null;
}

const PHASES_ORDER = [
    'loading_videos',
    'thumbnails',
    'transcripts',
    'comments',
    'retention',
    'embeddings',
    'complete',
];

interface Props {
    jobId: string;
    onComplete: () => void;
    onDismiss: () => void;
}

export default function SyncProgress({ jobId, onComplete, onDismiss }: Props) {
    const [job, setJob] = useState<JobStatus | null>(null);

    const poll = useCallback(async () => {
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/v1/jobs/${jobId}`);
            if (!res.ok) return;
            const data: JobStatus = await res.json();
            setJob(data);
            if (data.status === 'done') {
                onComplete();
            }
        } catch {
            // server may not be ready yet
        }
    }, [jobId, onComplete]);

    useEffect(() => {
        poll();
        const interval = setInterval(() => {
            poll().then(() => {
                if (job?.status === 'done' || job?.status === 'failed') {
                    clearInterval(interval);
                }
            });
        }, 2000);
        return () => clearInterval(interval);
    }, [poll, job?.status]);

    if (!job) return null;

    const isDone = job.status === 'done';
    const isFailed = job.status === 'failed';
    const phaseIndex = PHASES_ORDER.indexOf(job.phase);

    return (
        <div className="fixed bottom-6 right-6 z-50 w-96 bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl p-5">
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-2">
                    {isDone ? (
                        <CheckCircle size={20} className="text-emerald-400" />
                    ) : isFailed ? (
                        <XCircle size={20} className="text-red-400" />
                    ) : (
                        <Loader2 size={20} className="text-indigo-400 animate-spin" />
                    )}
                    <span className="font-semibold text-slate-200 text-sm">
                        {isDone ? 'Full Sync Complete' : isFailed ? 'Sync Failed' : 'Full Sync Running'}
                    </span>
                </div>
                {(isDone || isFailed) && (
                    <button
                        onClick={onDismiss}
                        className="text-slate-500 hover:text-slate-300 text-xs"
                    >
                        Dismiss
                    </button>
                )}
            </div>

            {/* Progress bar */}
            <div className="w-full bg-slate-700 rounded-full h-1.5 mb-4">
                <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${
                        isDone ? 'bg-emerald-500' : isFailed ? 'bg-red-500' : 'bg-indigo-500'
                    }`}
                    style={{ width: `${isDone ? 100 : job.progress}%` }}
                />
            </div>

            {/* Phase steps */}
            <div className="space-y-1.5">
                {PHASES_ORDER.filter(p => p !== 'loading_videos').map((phase, idx) => {
                    const adjustedPhaseIndex = phaseIndex - 1;
                    const isActive = PHASES_ORDER.indexOf(phase) === phaseIndex;
                    const isDonePhase = PHASES_ORDER.indexOf(phase) < phaseIndex || isDone;

                    return (
                        <div key={phase} className="flex items-center gap-2">
                            <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                                isDonePhase
                                    ? 'bg-emerald-400'
                                    : isActive
                                    ? 'bg-indigo-400 animate-pulse'
                                    : 'bg-slate-600'
                            }`} />
                            <span className={`text-xs ${
                                isDonePhase
                                    ? 'text-emerald-400'
                                    : isActive
                                    ? 'text-indigo-300 font-medium'
                                    : 'text-slate-500'
                            }`}>
                                {phase === 'complete' ? 'Complete' :
                                 phase === 'thumbnails' ? 'Thumbnails' :
                                 phase === 'transcripts' ? 'Transcripts' :
                                 phase === 'comments' ? 'Comments' :
                                 phase === 'retention' ? 'Retention Curves' :
                                 phase === 'embeddings' ? 'Vector Index' : phase}
                                {isActive && job.videos_total > 0 && (
                                    <span className="ml-1 text-slate-500">
                                        ({job.videos_done}/{job.videos_total})
                                    </span>
                                )}
                            </span>
                        </div>
                    );
                })}
            </div>

            {isFailed && job.error && (
                <p className="mt-3 text-xs text-red-400 bg-red-500/10 rounded-lg p-2">
                    {job.error}
                </p>
            )}
        </div>
    );
}
