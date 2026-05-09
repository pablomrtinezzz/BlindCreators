'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { BarChart2 } from 'lucide-react';

interface TimingData {
    publish_day_name: string;
    publish_hour: number;
    views: number;
}

interface TimingChartProps {
    data: TimingData[];
}

export default function TimingChart({ data }: { data: any[] }) {
    // 1. Transform backend data for the React chart component
    // We use optional chaining and fallbacks to prevent the 'substring' error
    const chartData = data.map(item => ({
        // Use 'day' (already shortened or full) and fallback to '??' if missing
        timeSlot: item.day || "???",
        // Use 'value' which represents the average views from our new API
        views: item.value ?? 0
    }));

    return (
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-8 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-xl font-bold text-slate-100">Publishing Performance</h2>
                    <p className="text-sm text-slate-400 mt-1">Average views based on historical publishing day</p>
                </div>
                {/* ... rest of your header ... */}
            </div>

            <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                        <XAxis
                            dataKey="timeSlot"
                            stroke="#94a3b8"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            stroke="#94a3b8"
                            fontSize={12}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(value) => `${(value / 1000).toFixed(1)}k`}
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f1f5f9' }}
                            itemStyle={{ color: '#818cf8' }}
                            cursor={{ fill: '#334155', opacity: 0.4 }}
                        />
                        <Bar
                            dataKey="views"
                            fill="#6366f1"
                            radius={[4, 4, 0, 0]}
                            barSize={40}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}