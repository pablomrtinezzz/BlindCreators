'use client';

import { LayoutDashboard, Sparkles, BarChart2, MessageSquare, FileText, BrainCircuit, Settings } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_SECTIONS = [
    {
        label: 'Analytics',
        items: [
            { name: 'Dashboard', href: '/', icon: <LayoutDashboard size={18} /> },
            { name: 'Retention', href: '/retention', icon: <BarChart2 size={18} /> },
        ],
    },
    {
        label: 'Content Intelligence',
        items: [
            { name: 'Transcripts', href: '/transcripts', icon: <FileText size={18} /> },
            { name: 'Comments', href: '/comments', icon: <MessageSquare size={18} /> },
        ],
    },
    {
        label: 'AI Engine',
        items: [
            { name: 'AI Tools', href: '/ai-tools', icon: <Sparkles size={18} /> },
            { name: 'RAG Chat', href: '/rag', icon: <BrainCircuit size={18} /> },
        ],
    },
    {
        label: 'System',
        items: [
            { name: 'Settings', href: '/settings', icon: <Settings size={18} /> },
        ],
    },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="w-64 bg-[#0B1120] border-r border-slate-800 flex flex-col hidden md:flex h-screen sticky top-0">
            {/* Branding */}
            <div className="h-20 flex items-center px-6 border-b border-slate-800">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
                        B
                    </div>
                    <span className="text-xl font-bold text-slate-100 tracking-tight">
                        BlindCreators
                    </span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-3 overflow-y-auto space-y-5">
                {NAV_SECTIONS.map((section) => (
                    <div key={section.label}>
                        <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-600">
                            {section.label}
                        </p>
                        <div className="space-y-0.5">
                            {section.items.map((item) => {
                                const isActive = pathname === item.href;
                                return (
                                    <Link
                                        key={item.name}
                                        href={item.href}
                                        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 group text-sm ${
                                            isActive
                                                ? 'bg-indigo-500/10 text-indigo-400 font-semibold border border-indigo-500/20'
                                                : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                                        }`}
                                    >
                                        <span className={isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'}>
                                            {item.icon}
                                        </span>
                                        {item.name}
                                        {isActive && (
                                            <div className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.8)]" />
                                        )}
                                    </Link>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </nav>

            {/* User stub */}
            <div className="p-3 border-t border-slate-800">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-slate-800/30 border border-slate-700/30 cursor-pointer hover:bg-slate-800/50 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
                        BC
                    </div>
                    <div className="flex flex-col">
                        <span className="text-sm font-semibold text-slate-200">BlindCreators</span>
                        <span className="text-xs text-slate-500">Pro Plan</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
