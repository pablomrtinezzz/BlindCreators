// frontend/src/components/Sidebar.tsx
'use client';

import { Calculator, LayoutDashboard, Settings, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
    // We get the current URL path to highlight the active menu item
    const pathname = usePathname();

    // Define our navigation structure
    const navItems = [
        { name: 'Dashboard', href: '/', icon: <LayoutDashboard size={20} /> },
        { name: 'AI Tools', href: '/ai-tools', icon: <Sparkles size={20} /> },
        { name: 'Calculator', href: '/calculator', icon: <Calculator size={20} /> },
        { name: 'Settings', href: '/settings', icon: <Settings size={20} /> },
    ];

    return (
        <div className="w-64 bg-[#0B1120] border-r border-slate-800 flex flex-col hidden md:flex h-screen sticky top-0">
            {/* App Logo & Branding */}
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

            {/* Navigation Links */}
            <nav className="flex-1 py-6 px-4 space-y-2">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;

                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive
                                    ? 'bg-indigo-500/10 text-indigo-400 font-semibold border border-indigo-500/20'
                                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                                }`}
                        >
                            <div className={`${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'}`}>
                                {item.icon}
                            </div>
                            {item.name}

                            {/* Active Indicator Dot */}
                            {isActive && (
                                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.8)]" />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* User Profile Section (Placeholder for Sprint 3) */}
            <div className="p-4 border-t border-slate-800">
                <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-800/30 border border-slate-700/30 cursor-pointer hover:bg-slate-800/50 transition-colors">
                    <div className="w-9 h-9 rounded-full bg-slate-700 flex items-center justify-center text-sm font-bold text-slate-300">
                        PR
                    </div>
                    <div className="flex flex-col">
                        <span className="text-sm font-semibold text-slate-200">Pablo</span>
                        <span className="text-xs text-slate-500">Pro Plan</span>
                    </div>
                </div>
            </div>
        </div>
    );
}