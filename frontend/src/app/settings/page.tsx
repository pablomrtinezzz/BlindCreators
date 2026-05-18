'use client';

import { useSession } from 'next-auth/react';
import { Settings, User, Key, Database, RefreshCw, Loader2 } from 'lucide-react';
import { useState } from 'react';

export default function SettingsPage() {
    const { data: session } = useSession();
    const [reindexing, setReindexing] = useState(false);
    const [reindexDone, setReindexDone] = useState(false);

    const email = session?.user?.email || '';

    const triggerReindex = async () => {
        if (!email) return;
        setReindexing(true);
        setReindexDone(false);
        try {
            await fetch('http://127.0.0.1:8000/api/v1/youtube/reindex', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_email: email }),
            });
            setReindexDone(true);
        } catch {
            // ignore
        } finally {
            setReindexing(false);
        }
    };

    return (
        <div className="p-8 max-w-3xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
                    <Settings className="text-slate-400" />
                    Settings
                </h1>
                <p className="text-slate-400 mt-2">Account and data management.</p>
            </div>

            <div className="space-y-4">
                {/* Account */}
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                        <User size={14} /> Account
                    </h2>
                    <div className="flex items-center gap-4">
                        {session?.user?.image && (
                            <img src={session.user.image} alt="" className="w-12 h-12 rounded-full border-2 border-slate-700" />
                        )}
                        <div>
                            <p className="font-semibold text-slate-200">{session?.user?.name ?? '—'}</p>
                            <p className="text-sm text-slate-400">{session?.user?.email ?? '—'}</p>
                        </div>
                    </div>
                </div>

                {/* API Scopes */}
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                        <Key size={14} /> Google OAuth Scopes
                    </h2>
                    <div className="space-y-2">
                        {[
                            { scope: 'youtube.readonly', label: 'YouTube Data API v3', desc: 'Read videos, comments, channel info' },
                            { scope: 'yt-analytics.readonly', label: 'YouTube Analytics API', desc: 'Audience retention curves per video' },
                        ].map(s => (
                            <div key={s.scope} className="flex items-start gap-3 p-3 bg-slate-900/40 rounded-xl">
                                <div className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                                <div>
                                    <p className="text-sm font-medium text-slate-300">{s.label}</p>
                                    <p className="text-xs text-slate-500">{s.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                    <p className="text-xs text-slate-600 mt-3">
                        If retention or comments are missing, sign out and sign in again to refresh your OAuth scopes.
                    </p>
                </div>

                {/* Data tools */}
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
                        <Database size={14} /> Data Tools
                    </h2>
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <p className="text-sm font-medium text-slate-300">Re-index Transcripts</p>
                            <p className="text-xs text-slate-500 mt-0.5">
                                Re-embed all existing transcript chunks into ChromaDB without running a Full Sync.
                                Use this after the AI model is updated or if RAG Chat shows stale results.
                            </p>
                        </div>
                        <button
                            onClick={triggerReindex}
                            disabled={reindexing || !email}
                            className="flex items-center gap-2 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-600/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 flex-shrink-0"
                        >
                            {reindexing ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                            {reindexing ? 'Running…' : reindexDone ? 'Done ✓' : 'Re-index'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
