'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { BarChart2, TrendingDown, Info, AlertTriangle, Loader2 } from 'lucide-react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';

interface RetentionPoint {
    elapsed_pct: number;
    watch_pct: number;
}

interface VideoRow {
    video_id: string;
    title: string;
    views: number;
    thumbnail_url: string;
}

export default function RetentionPage() {
    const { data: session } = useSession();
    const [videos, setVideos] = useState<VideoRow[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [curve, setCurve] = useState<RetentionPoint[]>([]);
    const [avgCurve, setAvgCurve] = useState<RetentionPoint[]>([]);
    const [loading, setLoading] = useState(false);
    const [noData, setNoData] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<any>(null);

    const email = session?.user?.email || '';

    useEffect(() => {
        if (!email) return;
        fetch(`http://127.0.0.1:8000/api/v1/videos/top?user_email=${email}`)
            .then(r => r.json())
            .then(d => setVideos(d.data || []));

        fetch(`http://127.0.0.1:8000/api/v1/retention/summary/${email}`)
            .then(r => r.json())
            .then(d => setAvgCurve(d.data || []));
    }, [email]);

    const handleTestAccess = async () => {
        // @ts-expect-error
        const token = session?.accessToken;
        if (!token || !email) return;
        setTesting(true);
        setTestResult(null);
        try {
            const res = await fetch('http://127.0.0.1:8000/api/v1/debug/test-retention', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ access_token: token, user_email: email }),
            });
            setTestResult(await res.json());
        } finally {
            setTesting(false);
        }
    };

    const loadRetention = async (videoId: string) => {
        setSelectedId(videoId);
        setLoading(true);
        setNoData(false);
        try {
            const res = await fetch(
                `http://127.0.0.1:8000/api/v1/retention/${videoId}?user_email=${email}`
            );
            if (res.status === 404) {
                setNoData(true);
                setCurve([]);
            } else {
                const d = await res.json();
                setCurve(d.data || []);
            }
        } finally {
            setLoading(false);
        }
    };

    const displayCurve = curve.length > 0 ? curve : avgCurve;
    const isAvg = curve.length === 0;

    const avgRetention = displayCurve.length
        ? Math.round(displayCurve.reduce((s, p) => s + p.watch_pct, 0) / displayCurve.length)
        : null;

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
                    <BarChart2 className="text-indigo-400" />
                    Audience Retention
                </h1>
                <p className="text-slate-400 mt-2">
                    Retention curves from YouTube Analytics API — see exactly where viewers drop off.
                </p>
            </div>

            {avgCurve.length === 0 && (
                <div className="mb-6 bg-slate-800/40 border border-amber-500/30 rounded-2xl p-5">
                    <div className="flex items-start gap-3 mb-4">
                        <AlertTriangle size={18} className="text-amber-400 mt-0.5 flex-shrink-0" />
                        <div>
                            <p className="text-amber-300 font-medium text-sm">No retention data indexed yet</p>
                            <p className="text-slate-400 text-xs mt-1">
                                Test your Analytics API access to find the exact error. Common causes: missing
                                <code className="mx-1 text-indigo-300">yt-analytics.readonly</code>scope (sign out → sign in again),
                                API not enabled in Google Cloud, or videos are YouTube Shorts (Analytics doesn't provide
                                retention curves for Shorts).
                            </p>
                        </div>
                    </div>

                    <button
                        onClick={handleTestAccess}
                        disabled={testing || !email}
                        className="flex items-center gap-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                        {testing ? <Loader2 size={14} className="animate-spin" /> : <AlertTriangle size={14} />}
                        {testing ? 'Testing…' : 'Test Analytics API Access'}
                    </button>

                    {testResult && (
                        <div className="mt-4 p-4 rounded-xl bg-slate-900/60 border border-slate-700">
                            <div className="flex items-center gap-2 mb-2">
                                <span className={`text-sm font-semibold ${testResult.http_status === 200 ? 'text-emerald-400' : 'text-red-400'}`}>
                                    HTTP {testResult.http_status}
                                </span>
                                <span className="text-xs text-slate-500 ml-auto">video: {testResult.video_id}</span>
                            </div>
                            {testResult.http_status === 200 && (
                                <p className="text-xs text-emerald-400 mb-2">
                                    API access works — {testResult.response?.rows?.length ?? 0} data points returned.
                                    {(testResult.response?.rows?.length ?? 0) === 0 && ' No retention data for this video (likely a Short or not enough views).'}
                                </p>
                            )}
                            {testResult.error && (
                                <p className="text-xs text-red-400 mb-2">Network error: {testResult.error}</p>
                            )}
                            <pre className="text-xs text-slate-600 font-mono overflow-auto max-h-40">
                                {JSON.stringify(testResult.response, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Video list */}
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4">
                    <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                        Select Video
                    </h2>
                    <div className="space-y-2">
                        <button
                            onClick={() => { setSelectedId(null); setCurve([]); setNoData(false); }}
                            className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors ${
                                !selectedId
                                    ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20'
                                    : 'text-slate-400 hover:bg-slate-700/50'
                            }`}
                        >
                            Channel Average
                        </button>
                        {videos.map(v => (
                            <button
                                key={v.video_id}
                                onClick={() => loadRetention(v.video_id)}
                                className={`w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors flex items-center gap-2 ${
                                    selectedId === v.video_id
                                        ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20'
                                        : 'text-slate-400 hover:bg-slate-700/50'
                                }`}
                            >
                                {v.thumbnail_url && (
                                    <img src={v.thumbnail_url} alt="" className="w-10 h-7 object-cover rounded flex-shrink-0" />
                                )}
                                <span className="truncate">{v.title}</span>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Chart */}
                <div className="lg:col-span-2 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
                    <div className="flex items-center justify-between mb-2">
                        <h2 className="text-lg font-semibold text-slate-200">
                            {isAvg ? 'Channel Average Retention' : `Retention: ${videos.find(v => v.video_id === selectedId)?.title ?? selectedId}`}
                        </h2>
                        {avgRetention !== null && (
                            <span className="text-sm text-slate-400">
                                Avg <span className="text-indigo-300 font-bold">{avgRetention}%</span> retained
                            </span>
                        )}
                    </div>

                    {loading ? (
                        <div className="h-64 flex items-center justify-center text-slate-500">
                            Loading retention data…
                        </div>
                    ) : noData ? (
                        <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
                            No retention data for this video yet. Run a Full Sync.
                        </div>
                    ) : displayCurve.length === 0 ? (
                        <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
                            No data available. Run a Full Sync first.
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={280}>
                            <LineChart data={displayCurve} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis
                                    dataKey="elapsed_pct"
                                    tickFormatter={v => `${v}%`}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    label={{ value: 'Video Progress', position: 'insideBottom', offset: -2, fill: '#475569', fontSize: 11 }}
                                />
                                <YAxis
                                    tickFormatter={v => `${v}%`}
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    domain={[0, 100]}
                                />
                                <Tooltip
                                    contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                                    labelFormatter={v => `${v}% into video`}
                                    formatter={(v: number) => [`${v}%`, 'Viewers still watching']}
                                />
                                <ReferenceLine y={50} stroke="#334155" strokeDasharray="4 2" label={{ value: '50%', fill: '#475569', fontSize: 10 }} />
                                <Line
                                    type="monotone"
                                    dataKey="watch_pct"
                                    stroke="#6366f1"
                                    strokeWidth={2.5}
                                    dot={false}
                                    activeDot={{ r: 5, fill: '#6366f1' }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    )}

                    <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
                        <TrendingDown size={14} />
                        Data sourced from YouTube Analytics API
                        {isAvg && ' · Averaged across all channel videos'}
                    </div>
                </div>
            </div>
        </div>
    );
}
