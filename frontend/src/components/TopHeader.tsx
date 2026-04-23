// frontend/src/components/TopHeader.tsx
import { Search, Bell } from 'lucide-react';

export default function TopHeader() {
    return (
        // Sticky header with a subtle blur effect
        <header className="h-20 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 sticky top-0 z-10">

            {/* Left side: Global Search Bar */}
            <div className="flex-1 max-w-md">
                <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search size={18} className="text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
                    </div>
                    <input
                        type="text"
                        placeholder="Search metrics, videos or AI prompts..."
                        className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-lg leading-5 bg-slate-800/50 text-slate-300 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 focus:bg-slate-800 transition-all sm:text-sm"
                    />
                </div>
            </div>

            {/* Right side: Notifications and Profile Area */}
            <div className="flex items-center gap-6">

                {/* Notification Bell with active badge */}
                <button className="relative p-2 text-slate-400 hover:text-slate-200 transition-colors rounded-full hover:bg-slate-800">
                    <Bell size={20} />
                    {/* Red notification dot */}
                    <span className="absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-rose-500 ring-2 ring-slate-900"></span>
                </button>

                {/* Profile Dropdown Placeholder */}
                <div className="flex items-center gap-3 cursor-pointer group border-l border-slate-800 pl-6">
                    <div className="hidden text-right md:block">
                        <p className="text-sm font-medium text-slate-200 group-hover:text-white transition-colors">Pablo</p>
                        <p className="text-xs text-slate-500 font-mono">Founder</p>
                    </div>
                    <div className="h-9 w-9 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 border-2 border-slate-800 shadow-md flex items-center justify-center text-white font-bold text-sm">
                        P
                    </div>
                </div>

            </div>
        </header>
    );
}