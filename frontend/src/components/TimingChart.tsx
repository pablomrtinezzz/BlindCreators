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

export default function TimingChart({ data }: TimingChartProps) {
    // Transform backend data for the React chart component
    const chartData = data.map(item => ({
        timeSlot: `${item.publish_day_name.substring(0, 3)} ${item.publish_hour}:00`,
        views: item.views
    }));

    return (
        <div className="bg-slate-800 p-6 rounded-xl border border-slate-700/50 shadow-lg w-full h-[450px] flex flex-col">
            <h3 className="text-white font-bold mb-6 flex items-center gap-2">
                <BarChart2 className="text-indigo-400" size={24} />
                Publishing Performance by Hour
            </h3>

            {/* Contenedor wrapper con altura estricta para evitar el error de Recharts */}
            <div className="flex-grow w-full h-full min-h-0">
                <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                    <BarChart data={chartData} margin={{ top: 20, right: 30, bottom: 60, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />

                        {/* Angled text for better readability of Days and Hours */}
                        <XAxis
                            dataKey="timeSlot"
                            stroke="#94a3b8"
                            fontSize={12}
                            tickMargin={10}
                            angle={-45}
                            textAnchor="end"
                        />

                        {/* Format the Y axis to show cleaner numbers (e.g., 15.2k) */}
                        <YAxis
                            stroke="#94a3b8"
                            fontSize={12}
                            tickFormatter={(value) => value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value}
                        />

                        <Tooltip
                            cursor={{ fill: '#1e293b' }}
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc', borderRadius: '0.5rem' }}
                            itemStyle={{ color: '#818cf8', fontWeight: 'bold' }}
                            formatter={(value: any) => [Number(value).toLocaleString(), "Avg Views"]}
                        />

                        <Bar
                            dataKey="views"
                            fill="#6366f1"
                            radius={[4, 4, 0, 0]}
                            animationDuration={1500}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}