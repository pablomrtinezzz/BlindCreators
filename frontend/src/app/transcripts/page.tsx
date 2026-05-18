'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { FileText, Clock, Globe, Cpu } from 'lucide-react';

interface TranscriptMeta {
    video_id: string;
    title: string;
    thumbnail_url: string | null;
    language: string;
    is_generated: boolean;
    word_count: number;
    fetched_at: string | null;
}

interface Chunk {
    index: number;
    text: string;
    start_sec: number;
    end_sec: number;
}

interface TranscriptDetail {
    video_id: string;
    language: string;
    is_generated: boolean;
    word_count: number;
    full_text: string;
    chunks: Chunk[];
}

function formatTime(sec: number) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function TranscriptsPage() {
    const { data: session } = useSession();
    const [transcripts, setTranscripts] = useState<TranscriptMeta[]>([]);
    const [selected, setSelected] = useState<TranscriptDetail | null>(null);
    const [loading, setLoading] = useState(false);
    const [listLoading, setListLoading] = useState(true);

    const email = session?.user?.email || '';

    useEffect(() => {
        if (!email) return;
        setListLoading(true);
        fetch(`http://127.0.0.1:8000/api/v1/transcripts?user_email=${email}`)
            .then(r => r.json())
            .then(d => setTranscripts(d.data || []))
            .finally(() => setListLoading(false));
    }, [email]);

    const loadDetail = async (videoId: string) => {
        setLoading(true);
        try {
            const res = await fetch(
                `http://127.0.0.1:8000/api/v1/transcripts/${videoId}?user_email=${email}`
            );
            if (res.ok) setSelected(await res.json());
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
                    <FileText className="text-purple-400" />
                    Transcripts
                </h1>
                <p className="text-slate-400 mt-2">
                    Full video transcripts indexed for semantic search. Click any video to read.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* List */}
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl p-4">
                    <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                        {transcripts.length} Indexed Videos
                    </h2>

                    {listLoading ? (
                        <div className="space-y-2">
                            {[...Array(4)].map((_, i) => (
                                <div key={i} className="h-14 bg-slate-700/30 rounded-xl animate-pulse" />
                            ))}
                        </div>
                    ) : transcripts.length === 0 ? (
                        <p className="text-sm text-slate-500 text-center py-8">
                            No transcripts yet. Run a Full Sync.
                        </p>
                    ) : (
                        <div className="space-y-1.5 max-h-[60vh] overflow-y-auto">
                            {transcripts.map(t => (
                                <button
                                    key={t.video_id}
                                    onClick={() => loadDetail(t.video_id)}
                                    className={`w-full text-left px-2 py-2.5 rounded-xl transition-colors flex items-center gap-2.5 group ${
                                        selected?.video_id === t.video_id
                                            ? 'bg-indigo-500/10 border border-indigo-500/20'
                                            : 'hover:bg-slate-700/50'
                                    }`}
                                >
                                    {t.thumbnail_url && (
                                        <img src={t.thumbnail_url} alt="" className="w-14 h-9 object-cover rounded flex-shrink-0" />
                                    )}
                                    <div className="flex-1 min-w-0">
                                        <p className={`text-xs font-medium leading-tight line-clamp-2 ${
                                            selected?.video_id === t.video_id ? 'text-indigo-300' : 'text-slate-300'
                                        }`}>
                                            {t.title}
                                        </p>
                                        <div className="flex items-center gap-1.5 mt-1">
                                            <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                                                <Globe size={9} />{t.language}
                                            </span>
                                            <span className="text-[10px] text-slate-500">{t.word_count.toLocaleString()}w</span>
                                            {t.is_generated && (
                                                <span className="text-[10px] text-amber-600 flex items-center gap-0.5">
                                                    <Cpu size={9} />auto
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Detail */}
                <div className="lg:col-span-2 bg-slate-800/40 border border-slate-700/50 rounded-2xl p-6">
                    {loading ? (
                        <div className="h-full flex items-center justify-center text-slate-500">
                            Loading transcript…
                        </div>
                    ) : !selected ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-600">
                            <FileText size={48} className="mb-4 opacity-20" />
                            <p className="text-sm">Select a video to read its transcript</p>
                        </div>
                    ) : (
                        <div>
                            <div className="flex items-start justify-between mb-4">
                                <div>
                                    <h2 className="text-lg font-semibold text-slate-200">{selected.video_id}</h2>
                                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                                        <span className="flex items-center gap-1"><Globe size={11} />{selected.language}</span>
                                        <span>{selected.word_count.toLocaleString()} words</span>
                                        <span>{selected.chunks.length} chunks indexed</span>
                                        {selected.is_generated && (
                                            <span className="text-amber-600 flex items-center gap-0.5">
                                                <Cpu size={11} />Auto-generated
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <a
                                    href={`https://youtube.com/watch?v=${selected.video_id}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-indigo-400 hover:text-indigo-300 border border-indigo-500/20 px-3 py-1.5 rounded-lg"
                                >
                                    Open on YouTube
                                </a>
                            </div>

                            <div className="space-y-3 max-h-[55vh] overflow-y-auto pr-1">
                                {selected.chunks.map(chunk => (
                                    <div
                                        key={chunk.index}
                                        className="bg-slate-900/50 border border-slate-700/50 rounded-xl p-4 hover:border-slate-600 transition-colors"
                                    >
                                        <div className="flex items-center gap-2 mb-2">
                                            <a
                                                href={`https://youtube.com/watch?v=${selected.video_id}&t=${Math.floor(chunk.start_sec)}s`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300"
                                            >
                                                <Clock size={11} />
                                                {formatTime(chunk.start_sec)} → {formatTime(chunk.end_sec)}
                                            </a>
                                            <span className="text-xs text-slate-600">Chunk #{chunk.index + 1}</span>
                                        </div>
                                        <p className="text-sm text-slate-300 leading-relaxed">{chunk.text}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
