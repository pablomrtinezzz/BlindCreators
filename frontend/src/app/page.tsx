// frontend/src/app/page.tsx
'use client';

import { useState, useEffect } from 'react';
import MetricCard from '../components/MetricCard';
import VideoCard from '../components/VideoCard';
import TimingChart from '../components/TimingChart';
import { Eye, ThumbsUp, Clock, Video, Activity } from 'lucide-react';

export default function DashboardPage() {
    const [kpis, setKpis] = useState<any>(null);
    const [topVideos, setTopVideos] = useState<any[]>([]);
    const [heatmapData, setHeatmapData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            fetch('http://127.0.0.1:8000/api/v1/metrics/overview'),
            fetch('http://127.0.0.1:8000/api/v1/videos/top'),
            fetch('http://127.0.0.1:8000/api/v1/metrics/heatmap')
        ])
            .then(async ([kpiRes, videosRes, heatmapRes]) => {
                const kpiData = await kpiRes.json();
                const videosData = await videosRes.json();
                const heatData = await heatmapRes.json();

                setKpis(kpiData);
                setTopVideos(videosData.data);
                setHeatmapData(heatData.data);
                setLoading(false);
            })
            .catch(error => {
                console.error("Error connecting to FastAPI:", error);
                setLoading(false);
            });
    }, []);

    // frontend/src/app/page.tsx (Replace the entire if (loading) block)

    if (loading) {
        return (
            <div className="min-h-screen p-8 max-w-7xl mx-auto w-full animate-pulse">
                {/* Header Skeleton */}
                <div className="mb-12 border-b border-slate-800 pb-6 flex justify-between items-end">
                    <div>
                        <div className="h-10 w-64 bg-slate-800 rounded-lg mb-4"></div>
                        <div className="h-4 w-48 bg-slate-800/50 rounded"></div>
                    </div>
                    <div className="h-8 w-40 bg-slate-800/50 rounded-full"></div>
                </div>

                {/* KPI Cards Skeleton */}
                <section className="mb-16">
                    <div className="h-6 w-48 bg-slate-800 rounded mb-6"></div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="bg-slate-800/40 h-[104px] rounded-xl border border-slate-700/30"></div>
                        ))}
                    </div>
                </section>

                {/* Chart Skeleton */}
                <section className="mb-16">
                    <div className="bg-slate-800/40 h-[400px] rounded-xl border border-slate-700/30 w-full flex items-center justify-center">
                        <div className="h-4 w-32 bg-slate-700/50 rounded"></div>
                    </div>
                </section>

                {/* Videos Skeleton */}
                <section>
                    <div className="h-6 w-48 bg-slate-800 rounded mb-6"></div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {[1, 2].map(i => (
                            <div key={i} className="bg-slate-800/40 h-32 rounded-xl border border-slate-700/30"></div>
                        ))}
                    </div>
                </section>
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
                    <p className="text-slate-400 font-medium">Decoupled Architecture: Next.js + FastAPI</p>
                </div>
                <div className="flex items-center gap-2 text-sm font-bold text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full border border-emerald-500/20">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                    Systems Synchronized
                </div>
            </header>

            <section className="mb-16">
                <h2 className="text-xl font-bold mb-6 text-white flex items-center gap-2">
                    <Activity size={24} className="text-indigo-400" />
                    Global Performance
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <MetricCard title="Total Views" value={kpis?.total_views.toLocaleString()} icon={<Eye size={24} />} accentColor="border-indigo-500" />
                    <MetricCard title="Engagement Rate" value={`${kpis?.avg_engagement}%`} icon={<ThumbsUp size={24} />} accentColor="border-emerald-500" />
                    <MetricCard title="Avg. Duration" value={`${kpis?.avg_duration_min}m`} icon={<Clock size={24} />} accentColor="border-pink-500" />
                    <MetricCard title="Indexed Videos" value={kpis?.total_videos} icon={<Video size={24} />} accentColor="border-purple-500" />
                </div>
            </section>

            {/* Analytics Chart Section */}
            <section className="mb-16">
                {heatmapData.length > 0 ? (
                    <TimingChart data={heatmapData} />
                ) : (
                    <div className="h-[400px] bg-slate-800/50 animate-pulse rounded-xl flex items-center justify-center text-slate-500 border border-slate-700/50">
                        Initializing graphical engine...
                    </div>
                )}
            </section>

            <section>
                <h2 className="text-xl font-bold mb-6 text-white flex items-center gap-2">
                    <span className="text-2xl">🏆</span> Hall of Fame
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {topVideos.map((video, index) => (
                        <VideoCard
                            key={video.video_id}
                            title={video.title}
                            views={video.views}
                            likes={video.likes}
                            thumbnailUrl={video.thumbnail_url}
                            duration={video.formatted_duration}
                            rank={index + 1}
                        />
                    ))}
                </div>
            </section>
        </div>
    );
} 