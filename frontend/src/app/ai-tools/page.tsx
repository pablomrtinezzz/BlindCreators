// frontend/src/app/ai-tools/page.tsx
'use client';

import { useState } from 'react';
import { Sparkles, MessageSquare, Send, Loader2, Target } from 'lucide-react';

export default function AIToolsPage() {
    // State for Title Generator
    const [topic, setTopic] = useState('');
    const [instructions, setInstructions] = useState('');
    const [titles, setTitles] = useState<string[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);

    // State for Audience Miner
    const [insights, setInsights] = useState('');
    const [isMining, setIsMining] = useState(false);

    // Function to call FastAPI for titles
    const handleGenerateTitles = async () => {
        if (!topic) return;

        setIsGenerating(true);
        setTitles([]);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/ai/generate-titles', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic: topic,
                    extra_instructions: instructions || null
                }),
            });

            const result = await response.json();
            setTitles(result.data || []);
        } catch (error) {
            console.error("Failed to generate titles:", error);
            setTitles(["Error connecting to AI engine. Please check backend."]);
        } finally {
            setIsGenerating(false);
        }
    };

    // Function to call FastAPI for audience insights
    const handleMineAudience = async () => {
        setIsMining(true);
        setInsights('');

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/ai/audience-insights');
            const result = await response.json();
            setInsights(result.data || "No insights generated.");
        } catch (error) {
            console.error("Failed to mine audience:", error);
            setInsights("Error connecting to AI engine.");
        } finally {
            setIsMining(false);
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto w-full">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
                    <Sparkles className="text-indigo-400" />
                    AI Content Engine
                </h1>
                <p className="text-slate-400 mt-2">
                    Leverage your historical data and audience sentiment to engineer viral content.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                {/* LEFT COLUMN: Title Generator Form */}
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm flex flex-col h-full">
                    <div className="flex items-center gap-2 mb-6">
                        <Target className="text-purple-400" size={24} />
                        <h2 className="text-xl font-semibold text-slate-200">Concept Generator</h2>
                    </div>

                    <div className="space-y-5 flex-1">
                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">
                                Core Topic / Video Idea
                            </label>
                            <textarea
                                value={topic}
                                onChange={(e) => setTopic(e.target.value)}
                                placeholder="e.g., A deep dive into Elden Ring's hardest boss..."
                                className="w-full bg-slate-900/50 border border-slate-700 rounded-xl p-4 text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all resize-none h-28"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-400 mb-2">
                                Vibe / Instructions (Optional)
                            </label>
                            <input
                                type="text"
                                value={instructions}
                                onChange={(e) => setInstructions(e.target.value)}
                                placeholder="e.g., Make it mysterious, no clickbait."
                                className="w-full bg-slate-900/50 border border-slate-700 rounded-xl p-4 text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            />
                        </div>
                    </div>

                    <button
                        onClick={handleGenerateTitles}
                        disabled={!topic || isGenerating}
                        className="mt-6 w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-4 rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(79,70,229,0.3)]"
                    >
                        {isGenerating ? (
                            <Loader2 className="animate-spin" size={20} />
                        ) : (
                            <Send size={20} />
                        )}
                        {isGenerating ? 'Engineering Titles...' : 'Generate SEO Titles'}
                    </button>
                </div>

                {/* RIGHT COLUMN: Results & Miner */}
                <div className="space-y-8 flex flex-col h-full">

                    {/* Title Results Card */}
                    <div className="bg-indigo-900/10 border border-indigo-500/20 rounded-2xl p-6 backdrop-blur-sm flex-1">
                        <h3 className="text-sm font-semibold text-indigo-400 tracking-wider uppercase mb-4">
                            AI Suggestions
                        </h3>

                        {titles.length === 0 && !isGenerating && (
                            <div className="h-full flex flex-col items-center justify-center text-slate-500 min-h-[150px]">
                                <Sparkles size={32} className="mb-3 opacity-20" />
                                <p className="text-sm">Your generated titles will appear here</p>
                            </div>
                        )}

                        <div className="space-y-3">
                            {titles.map((title, index) => (
                                <div key={index} className="bg-slate-900/50 border border-slate-700/50 p-4 rounded-xl text-slate-200 shadow-sm">
                                    {title}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Audience Miner Card */}
                    <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <MessageSquare className="text-emerald-400" size={24} />
                                <h2 className="text-xl font-semibold text-slate-200">Audience Miner</h2>
                            </div>
                            <button
                                onClick={handleMineAudience}
                                disabled={isMining}
                                className="bg-slate-700 hover:bg-slate-600 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
                            >
                                {isMining ? <Loader2 className="animate-spin" size={16} /> : <Sparkles size={16} />}
                                Mine Comments
                            </button>
                        </div>

                        <p className="text-sm text-slate-400 mb-4">
                            Extract real desires and video concepts directly from your historical YouTube comments.
                        </p>

                        {insights && (
                            <div className="bg-slate-900/50 border border-slate-700/50 p-5 rounded-xl text-sm text-slate-300 leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap">
                                {insights}
                            </div>
                        )}
                    </div>

                </div>
            </div>
        </div>
    );
}