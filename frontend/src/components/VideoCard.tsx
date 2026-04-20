// frontend/src/components/VideoCard.tsx
import { Clock, Eye, ThumbsUp } from 'lucide-react';

interface VideoProps {
    title: string;
    views: number;
    likes: number;
    thumbnailUrl: string;
    duration: string;
    rank: number;
}

export default function VideoCard({ title, views, likes, thumbnailUrl, duration, rank }: VideoProps) {
    return (
        <div className="flex bg-slate-800/40 hover:bg-slate-800 border border-slate-700/50 rounded-xl overflow-hidden transition-all duration-300 group">
        
        {/* Thumbnail Section */}
        <div className="relative w-56 shrink-0 overflow-hidden">
            <img 
            src={thumbnailUrl || '/api/placeholder/400/300'}
            alt={title} 
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
            <div className="absolute bottom-2 right-2 bg-slate-900/90 backdrop-blur-sm px-2 py-1 rounded text-xs font-mono text-white flex items-center gap-1">
            <Clock size={12} /> {duration}
            </div>
            <div className="absolute top-0 left-0 bg-indigo-500 w-8 h-8 flex items-center justify-center font-bold text-white rounded-br-lg shadow-lg">
            #{rank}
            </div>
        </div>

      {/* Info Section */}
        <div className="p-5 flex flex-col justify-between w-full">
            <h4 className="text-slate-100 font-semibold text-lg line-clamp-2 leading-tight">
            {title}
            </h4>
            
            <div className="flex gap-6 mt-4 text-sm font-medium">
            <div className="flex items-center gap-1.5 text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-full">
                <Eye size={16} /> 
                {views.toLocaleString()}
            </div>
            <div className="flex items-center gap-1.5 text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full">
                <ThumbsUp size={16} /> 
                {likes.toLocaleString()}
            </div>
            </div>
        </div>
        
        </div>
    );
}