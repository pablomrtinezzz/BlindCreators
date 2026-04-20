import React from 'react';

interface MetricCardProps {
    title: string;
    value: string | number;
    icon: React.ReactNode;
    accentColor?: string;
}

export default function MetricCard({ title, value, icon, accentColor = "border-indigo-500" }: MetricCardProps) {
return (
    <div className={`bg-slate-800 p-6 rounded-xl border-l-4 ${accentColor} shadow-lg transition-transform hover:-translate-y-1 duration-300`}>
    <div className="flex justify-between items-start">
        <div>
        <h3 className="text-slate-400 text-xs font-bold tracking-widest uppercase mb-2">
            {title}
        </h3>
        <p className="text-3xl font-extrabold text-white">
            {value}
        </p>
        </div>
        <div className={`p-3 bg-slate-700/50 rounded-lg text-slate-300`}>
        {icon}
        </div>
    </div>
    </div>
);
}