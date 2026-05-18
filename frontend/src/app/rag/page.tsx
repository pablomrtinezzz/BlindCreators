'use client';

import { useState, useRef, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { BrainCircuit, Send, Loader2, ExternalLink, Clock, MessageSquare } from 'lucide-react';

interface Source {
    video_id: string;
    video_title: string;
    start_sec: number;
    score: number;
    type?: string;
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
}

const SUGGESTED = [
    "What topics do my viewers ask about most?",
    "Which videos have the most detailed explanations?",
    "What recurring themes appear across my content?",
    "Where do I usually introduce the main topic?",
];

function formatTime(sec: number) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function RAGPage() {
    const { data: session } = useSession();
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    const email = session?.user?.email || '';

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async (text: string) => {
        if (!text.trim() || !email || loading) return;

        const userMsg: Message = { role: 'user', content: text };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await fetch(
                `http://127.0.0.1:8000/api/v1/ai/rag-query?user_email=${email}`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: text, top_k: 5 }),
                }
            );

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }

            const data = await res.json();
            setMessages(prev => [
                ...prev,
                {
                    role: 'assistant',
                    content: data.answer,
                    sources: data.sources,
                },
            ]);
        } catch (err) {
            setMessages(prev => [
                ...prev,
                {
                    role: 'assistant',
                    content: 'Error connecting to the AI engine. Make sure the backend is running and a Full Sync has been completed.',
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-5rem)] max-w-4xl mx-auto p-6">
            {/* Header */}
            <div className="mb-6">
                <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
                    <BrainCircuit className="text-indigo-400" />
                    RAG Chat
                </h1>
                <p className="text-slate-400 mt-1 text-sm">
                    Ask anything about your channel — answers are grounded in your video transcripts and viewer comments.
                </p>
            </div>

            {/* Chat area */}
            <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-1">
                {messages.length === 0 && (
                    <div className="py-8">
                        <div className="grid grid-cols-2 gap-3">
                            {SUGGESTED.map(s => (
                                <button
                                    key={s}
                                    onClick={() => sendMessage(s)}
                                    className="text-left bg-slate-800/40 border border-slate-700/50 hover:border-indigo-500/30 hover:bg-indigo-500/5 rounded-xl p-4 text-sm text-slate-400 transition-colors"
                                >
                                    {s}
                                </button>
                            ))}
                        </div>
                        <p className="text-center text-xs text-slate-600 mt-6">
                            Powered by Gemini 2.5 Flash + ChromaDB vector search over your transcripts and viewer comments
                        </p>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-last' : ''}`}>
                            <div className={`rounded-2xl px-4 py-3 ${
                                msg.role === 'user'
                                    ? 'bg-indigo-600 text-white'
                                    : 'bg-slate-800/60 border border-slate-700/50 text-slate-200'
                            }`}>
                                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                            </div>

                            {/* Sources */}
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-2 space-y-1.5">
                                    <p className="text-xs text-slate-600 px-1">Sources used:</p>
                                    {msg.sources.map((src, j) => {
                                        const isComment = src.type === 'comment';
                                        return isComment ? (
                                            <div
                                                key={j}
                                                className="flex items-center gap-2 bg-slate-800/40 border border-emerald-700/20 rounded-lg px-3 py-1.5"
                                            >
                                                <MessageSquare size={11} className="text-emerald-500/60 flex-shrink-0" />
                                                <span className="text-xs text-slate-400 truncate">
                                                    {src.video_title || src.video_id}
                                                </span>
                                                <span className="text-[10px] text-emerald-600 ml-auto flex-shrink-0">comments</span>
                                                <span className="text-xs text-indigo-500/60 flex-shrink-0">
                                                    {(src.score * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        ) : (
                                            <a
                                                key={j}
                                                href={`https://youtube.com/watch?v=${src.video_id}&t=${Math.floor(src.start_sec)}s`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-2 bg-slate-800/40 border border-slate-700/30 hover:border-indigo-500/30 rounded-lg px-3 py-1.5 transition-colors group"
                                            >
                                                <ExternalLink size={11} className="text-slate-600 group-hover:text-indigo-400 flex-shrink-0" />
                                                <span className="text-xs text-slate-400 truncate group-hover:text-slate-300">
                                                    {src.video_title || src.video_id}
                                                </span>
                                                <span className="flex items-center gap-0.5 text-xs text-slate-600 ml-auto flex-shrink-0">
                                                    <Clock size={10} />
                                                    {formatTime(src.start_sec)}
                                                </span>
                                                <span className="text-xs text-indigo-500/60 flex-shrink-0">
                                                    {(src.score * 100).toFixed(0)}%
                                                </span>
                                            </a>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl px-4 py-3 flex items-center gap-2">
                            <Loader2 size={14} className="text-indigo-400 animate-spin" />
                            <span className="text-xs text-slate-500">Searching transcripts and comments…</span>
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="flex items-center gap-3 bg-slate-800/50 border border-slate-700 rounded-2xl px-4 py-3">
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
                    placeholder="Ask about your channel's content..."
                    className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 focus:outline-none"
                    disabled={loading}
                />
                <button
                    onClick={() => sendMessage(input)}
                    disabled={!input.trim() || loading || !email}
                    className="w-8 h-8 flex items-center justify-center bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 rounded-xl transition-colors flex-shrink-0"
                >
                    <Send size={14} className="text-white" />
                </button>
            </div>
        </div>
    );
}
