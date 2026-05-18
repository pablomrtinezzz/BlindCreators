'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { MessageSquare, ThumbsUp, Reply, Search, AlertTriangle, CheckCircle, Loader2, XCircle } from 'lucide-react';

interface Comment {
    comment_id: string;
    video_id: string;
    author: string;
    text: string;
    likes: number;
    reply_count: number;
    published_at: string | null;
}

interface Summary {
    total_comments: number;
    data: Comment[];
}

const STATUS_INFO: Record<string, { icon: typeof CheckCircle; color: string; title: string; fix: string }> = {
    ok:            { icon: CheckCircle, color: 'text-emerald-400', title: 'Access OK', fix: '' },
    token_expired: { icon: XCircle, color: 'text-red-400', title: 'Access token expired', fix: 'Sign out and sign in again, then run Full Sync immediately.' },
    disabled:      { icon: AlertTriangle, color: 'text-amber-400', title: 'Comments disabled on this video', fix: 'YouTube confirmed comments are off on this specific video (commentsDisabled). If all your videos are Shorts, YouTube may have disabled comments on all of them. Check YouTube Studio → Content → select a video → Comments.' },
    no_permission: { icon: XCircle, color: 'text-red-400', title: 'API access forbidden', fix: 'The YouTube API returned "forbidden" — not a comments-disabled error. Try: sign out → sign in again to refresh scopes. If still failing, go to myaccount.google.com/permissions, revoke BlindCreators, and sign in again.' },
    error:         { icon: XCircle, color: 'text-red-400', title: 'API error', fix: 'Check backend logs for details.' },
};

export default function CommentsPage() {
    const { data: session } = useSession();
    const [summary, setSummary] = useState<Summary | null>(null);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ video_id: string; result: any } | null>(null);

    const email = session?.user?.email || '';

    useEffect(() => {
        if (!email) return;
        setLoading(true);
        fetch(`http://127.0.0.1:8000/api/v1/comments/summary/${email}`)
            .then(r => r.json())
            .then(d => setSummary(d))
            .finally(() => setLoading(false));
    }, [email]);

    const handleTestAccess = async () => {
        // @ts-expect-error
        const token = session?.accessToken;
        if (!token || !email) return;
        setTesting(true);
        setTestResult(null);
        try {
            const res = await fetch('http://127.0.0.1:8000/api/v1/debug/test-comments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ access_token: token, user_email: email }),
            });
            setTestResult(await res.json());
        } finally {
            setTesting(false);
        }
    };

    const filtered = (summary?.data || []).filter(c =>
        c.text.toLowerCase().includes(search.toLowerCase()) ||
        c.author.toLowerCase().includes(search.toLowerCase())
    );

    const isEmpty = !loading && (summary?.total_comments ?? 0) === 0;

    // Map raw YouTube HTTP status + error reason to our STATUS_INFO key
    const deriveStatusKey = (result: any): string | undefined => {
        if (!result) return undefined;
        const http = result.http_status;
        if (http === 200) return 'ok';
        if (http === 401) return 'token_expired';
        if (http === 403) {
            const reason = result.response?.error?.errors?.[0]?.reason ?? '';
            return reason === 'commentsDisabled' ? 'disabled' : 'no_permission';
        }
        return 'error';
    };
    const statusKey = deriveStatusKey(testResult);
    const statusInfo = statusKey ? STATUS_INFO[statusKey] : null;

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
                    <MessageSquare className="text-emerald-400" />
                    Comment Mining
                </h1>
                <p className="text-slate-400 mt-2">Top comments across your entire channel, ordered by engagement.</p>
            </div>

            {/* Diagnostic panel — shown when comments are 0 */}
            {isEmpty && (
                <div className="mb-6 bg-slate-800/40 border border-amber-500/30 rounded-2xl p-5">
                    <div className="flex items-start gap-3 mb-4">
                        <AlertTriangle size={18} className="text-amber-400 mt-0.5 flex-shrink-0" />
                        <div>
                            <p className="text-amber-300 font-medium text-sm">No comments indexed yet</p>
                            <p className="text-slate-400 text-xs mt-1">
                                Test your API access to find out why. Common causes: token expired, comments disabled on all videos, or missing OAuth scope.
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={handleTestAccess}
                        disabled={testing || !email}
                        className="flex items-center gap-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                        {testing ? <Loader2 size={14} className="animate-spin" /> : <AlertTriangle size={14} />}
                        {testing ? 'Testing…' : 'Test Comment API Access'}
                    </button>

                    {testResult && (
                        <div className="mt-4 p-4 rounded-xl bg-slate-900/60 border border-slate-700">
                            <div className="flex items-center gap-2 mb-2">
                                {statusInfo && <statusInfo.icon size={16} className={statusInfo.color} />}
                                <span className={`font-semibold text-sm ${statusInfo?.color ?? 'text-slate-400'}`}>
                                    {statusInfo?.title ?? `HTTP ${testResult.http_status}`}
                                </span>
                                <span className="text-xs text-slate-500 ml-auto">video: {testResult.video_id}</span>
                            </div>
                            {statusKey === 'ok' && (
                                <p className="text-xs text-emerald-400 mb-1">
                                    API access works — {testResult.response?.pageInfo?.totalResults ?? 0} comments on this video.
                                    Run a Full Sync to index all videos.
                                </p>
                            )}
                            {statusInfo?.fix && (
                                <p className="text-xs text-slate-400 mt-1 mb-2">{statusInfo.fix}</p>
                            )}
                            <pre className="text-xs text-slate-600 mt-2 font-mono overflow-auto max-h-48">
                                {JSON.stringify(testResult.response, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}

            {/* Stats bar */}
            {summary && !isEmpty && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
                    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Total Indexed</p>
                        <p className="text-2xl font-bold text-slate-100">{summary.total_comments.toLocaleString()}</p>
                        <p className="text-xs text-slate-500 mt-1">comments</p>
                    </div>
                    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Shown</p>
                        <p className="text-2xl font-bold text-emerald-400">{filtered.length}</p>
                        <p className="text-xs text-slate-500 mt-1">top by likes</p>
                    </div>
                    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4">
                        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Top Comment Likes</p>
                        <p className="text-2xl font-bold text-indigo-400">
                            {summary.data[0]?.likes?.toLocaleString() ?? 0}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">likes on #1</p>
                    </div>
                </div>
            )}

            {/* Search */}
            {!isEmpty && (
                <div className="relative mb-6">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Search comments or authors..."
                        className="w-full pl-9 pr-4 py-2.5 bg-slate-800/50 border border-slate-700 rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                </div>
            )}

            {/* Comment list */}
            {loading ? (
                <div className="space-y-3">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="bg-slate-800/40 h-24 rounded-xl animate-pulse border border-slate-700/30" />
                    ))}
                </div>
            ) : filtered.length > 0 ? (
                <div className="space-y-3">
                    {filtered.map(comment => (
                        <div key={comment.comment_id} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 hover:border-slate-600 transition-colors">
                            <div className="flex items-start justify-between gap-4">
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
                                            {comment.author.charAt(0).toUpperCase()}
                                        </div>
                                        <span className="text-sm font-medium text-slate-300">{comment.author}</span>
                                        {comment.published_at && (
                                            <span className="text-xs text-slate-600">
                                                {new Date(comment.published_at).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-slate-300 leading-relaxed">{comment.text}</p>
                                </div>
                                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                                    <div className="flex items-center gap-1 text-xs text-slate-500">
                                        <ThumbsUp size={12} />
                                        <span>{comment.likes.toLocaleString()}</span>
                                    </div>
                                    {comment.reply_count > 0 && (
                                        <div className="flex items-center gap-1 text-xs text-slate-600">
                                            <Reply size={12} />
                                            <span>{comment.reply_count}</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div className="mt-2 pt-2 border-t border-slate-700/50">
                                <a
                                    href={`https://youtube.com/watch?v=${comment.video_id}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                                >
                                    → Watch on YouTube
                                </a>
                            </div>
                        </div>
                    ))}
                </div>
            ) : null}
        </div>
    );
}
