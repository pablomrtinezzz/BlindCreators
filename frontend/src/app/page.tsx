// frontend/src/app/page.tsx
'use client';

import { useState, useEffect, useCallback } from 'react';
import MetricCard from '../components/MetricCard';
import VideoCard from '../components/VideoCard';
import TimingChart from '../components/TimingChart';
import { Eye, ThumbsUp, Clock, Video, Activity } from 'lucide-react';
import { useSession } from "next-auth/react";

export default function DashboardPage() {
    const { data: session } = useSession();
    const [kpis, setKpis] = useState<any>(null);
    const [topVideos, setTopVideos] = useState<any[]>([]);
    const [heatmapData, setHeatmapData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    /**
     * Function to fetch all data from the backend.
     * Wrapped in useCallback to prevent unnecessary re-renders.
     */
    const fetchData = useCallback(async () => {
        const userEmail = session?.user?.email || "dailypodcasts012@gmail.com";
        setLoading(true);

        try {
            const [kpiRes, videosRes, heatmapRes] = await Promise.all([
                fetch(`http://127.0.0.1:8000/api/v1/metrics/overview?user_email=${userEmail}`),
                fetch(`http://127.0.0.1:8000/api/v1/videos/top?user_email=${userEmail}`),
                fetch(`http://127.0.0.1:8000/api/v1/metrics/heatmap?user_email=${userEmail}`)
            ]);

            const kpiData = await kpiRes.json();
            const videosData = await videosRes.json();
            const heatData = await heatmapRes.json();

            setKpis(kpiData);
            setTopVideos(videosData.data || []);
            setHeatmapData(heatData.data || []);
        } catch (error) {
            console.error("Failed to fetch dashboard data:", error);
        } finally {
            setLoading(false);
        }
    }, [session]);

    /**
     * Initial data load when the session is ready.
     */
    useEffect(() => {
        if (session) {
            fetchData();
        }
    }, [session, fetchData]);

    /**
     * Listen for a custom event 'sync-complete' to trigger a data refresh.
     * This allows the TopHeader component to notify the Dashboard when a sync finishes.
     */
    useEffect(() => {
        window.addEventListener('sync-complete', fetchData);
        return () => window.removeEventListener('sync-complete', fetchData);
    }, [fetchData]);

    if (loading) {
        return (
            <div className="min-h-screen p-8 max-w-7xl mx-auto w-full animate-pulse">
                <div className="mb-12 border-b border-slate-800 pb-6 flex justify-between items-end">
                    <div>
                        <div className="h-10 w-64 bg-slate-800 rounded-lg mb-4"></div>
                        <div className="h-4 w-48 bg-slate-800/50 rounded"></div>
                    </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="bg-slate-800/40 h-24 rounded-xl border border-slate-700/30"></div>
                    ))}
                </div>
                <div className="bg-slate-800/40 h-[400px] rounded-xl border border-slate-700/30 w-full"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen p-8 max-w-7xl mx-auto">
            <header className="mb-12 border-b border-slate-800 pb-6 flex justify-between items-end">
                <div>
                    <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-500 mb-2">
                        Executive Analytics
                    </h1>
                    <p className="text-slate-400 font-medium">Channel: {session?.user?.name || 'Daily Podcasts'}</p>
                </div>
                <div className="flex items-center gap-2 text-sm font-bold text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full border border-emerald-500/20">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                    Systems Synchronized
                </div>
            </header>

            {/* KPI Grid - CORREGIDO */}
            <section className="mb-16">
                <h2 className="text-xl font-bold mb-6 text-white flex items-center gap-2">
                    <Activity size={24} className="text-indigo-400" />
                    Global Performance
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <MetricCard
                        title="Total Views"
                        value={kpis?.total_views?.toLocaleString() ?? "0"}
                        icon={<Eye size={24} />}
                        accentColor="border-indigo-500"
                    />
                    <MetricCard
                        title="Engagement Rate"
                        value={`${kpis?.avg_engagement ?? 0}%`}
                        icon={<ThumbsUp size={24} />}
                        accentColor="border-emerald-500"
                    />
                    <MetricCard
                        title="Avg. Duration"
                        value={`${kpis?.avg_duration_min ?? 0}m`}
                        icon={<Clock size={24} />}
                        accentColor="border-pink-500"
                    />
                    <MetricCard
                        title="Indexed Videos"
                        value={kpis?.total_videos ?? 0}
                        icon={<Video size={24} />}
                        accentColor="border-purple-500"
                    />
                </div>
            </section>

            {/* Analytics Chart Section - CORREGIDO */}
            <section className="mb-16">
                {(heatmapData?.length ?? 0) > 0 ? (
                    <TimingChart data={heatmapData} />
                ) : (
                    <div className="h-[400px] bg-slate-800/50 rounded-xl flex items-center justify-center text-slate-500 border border-slate-700/50">
                        <div className="text-center">
                            <p>No performance data available for this channel.</p>
                            <p className="text-xs mt-2 text-slate-600">Click "Sync My Channel" to fetch data.</p>
                        </div>
                    </div>
                )}
            </section>

            {/* Hall of Fame - CORREGIDO */}
            <section>
                <h2 className="text-xl font-bold mb-6 text-white flex items-center gap-2">
                    <span className="text-2xl">🏆</span> Hall of Fame
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {(topVideos?.length ?? 0) > 0 ? (
                        topVideos.map((video, index) => (
                            <VideoCard
                                key={video.video_id || index}
                                title={video.title || "Untitled Video"}
                                views={video.views ?? 0}
                                likes={video.likes ?? 0}
                                thumbnailUrl={video.thumbnail_url || ""}
                                duration={`${Math.floor((video.duration_sec ?? 0) / 60)}m`}
                                rank={index + 1}
                            />
                        ))
                    ) : (
                        <div className="col-span-full py-12 text-center text-slate-500 bg-slate-800/20 rounded-xl border border-dashed border-slate-700">
                            No videos found. Use the sync button to begin.
                        </div>
                    )}
                </div>
            </section>
        </div>
    );
}