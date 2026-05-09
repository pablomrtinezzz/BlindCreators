// frontend/src/components/TopHeader.tsx
'use client';

import { useState } from 'react';
import { Search, Bell, LogOut, LogIn, RefreshCw } from 'lucide-react';
import { useSession, signIn, signOut } from "next-auth/react";

export default function TopHeader() {
    const { data: session, status } = useSession();
    const [isSyncing, setIsSyncing] = useState(false);

    /**
     * Triggers the real-time ETL pipeline in the Python backend.
     * After success, it notifies the Dashboard to refresh data.
     */
    const syncYouTubeData = async () => {
    // 1. Safety check: Is the session even there?
    if (!session) {
        alert("Session not found. Please log in again.");
        return;
    }

    // @ts-expect-error - Custom property added in route.ts
    const token = session.accessToken;
    const email = session.user?.email;

    // 2. Explicit check for token and email
    if (!token || !email) {
        console.error("Missing credentials:", { token: !!token, email: !!email });
        alert("Credentials missing. Please log out and log back in to refresh your Google permissions.");
        return;
    }

    setIsSyncing(true);

    try {
        const response = await fetch("http://127.0.0.1:8000/api/v1/youtube/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                access_token: token,
                user_email: email
            }),
        });

        const data = await response.json();

        if (data.status === 'success') {
            alert(`✅ Success! Synced ${data.videos_synced} videos.`);
            window.dispatchEvent(new Event('sync-complete'));
        } else {
            alert(`❌ Error: ${data.message || "Unknown error from server"}`);
        }
    } catch (error) {
        console.error("Fetch error:", error);
        alert("Could not connect to the backend. Is your Python server running?");
    } finally {
        setIsSyncing(false);
    }
};

    return (
        <header className="h-20 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 sticky top-0 z-10">
            <div className="flex-1 max-w-md">
                <div className="relative group">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search size={18} className="text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
                    </div>
                    <input
                        type="text"
                        placeholder="Search metrics, videos or AI prompts..."
                        className="block w-full pl-10 pr-3 py-2 border border-slate-700 rounded-lg bg-slate-800/50 text-slate-300 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all sm:text-sm"
                    />
                </div>
            </div>

            <div className="flex items-center gap-6">
                {/* Real Sync Button */}
                {session?.user && (
                    <button
                        onClick={syncYouTubeData}
                        disabled={isSyncing}
                        className="flex items-center gap-2 bg-emerald-600/10 hover:bg-emerald-600/20 text-emerald-500 border border-emerald-600/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                    >
                        <RefreshCw size={16} className={isSyncing ? "animate-spin" : ""} />
                        {isSyncing ? "Syncing..." : "Sync My Channel"}
                    </button>
                )}

                <button className="relative p-2 text-slate-400 hover:text-slate-200 transition-colors rounded-full hover:bg-slate-800">
                    <Bell size={20} />
                    <span className="absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-rose-500 ring-2 ring-slate-900"></span>
                </button>

                <div className="border-l border-slate-800 pl-6">
                    {status === 'loading' ? (
                        <div className="h-9 w-9 rounded-full bg-slate-800 animate-pulse"></div>
                    ) : session?.user ? (
                        <div className="flex items-center gap-3 group">
                            <div className="hidden text-right md:block">
                                <p className="text-sm font-medium text-slate-200">{session.user.name}</p>
                                <button
                                    onClick={() => signOut()}
                                    className="text-xs text-slate-500 hover:text-rose-400 transition-colors flex items-center gap-1 justify-end w-full"
                                >
                                    <LogOut size={12} /> Sign Out
                                </button>
                            </div>
                            <img
                                src={session.user.image || ''}
                                alt="Profile"
                                className="h-9 w-9 rounded-full border-2 border-slate-700 shadow-md"
                            />
                        </div>
                    ) : (
                        <button
                            onClick={() => signIn('google')}
                            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                        >
                            <LogIn size={16} />
                            Sign in with Google
                        </button>
                    )}
                </div>
            </div>
        </header>
    );
}