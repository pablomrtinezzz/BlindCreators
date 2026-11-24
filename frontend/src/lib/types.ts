export type JobStatus = "pending" | "running" | "done" | "partial" | "failed" | "interrupted";

export interface SyncJob {
  id: string;
  status: JobStatus;
  phase: string;
  phase_index: number | null;
  phases: string[];
  done: number;
  total: number;
  message: string | null;
  stats: Record<string, Record<string, number>>;
  created_at: string | null;
  finished_at: string | null;
}

export interface Me {
  email: string;
  name: string;
  image: string | null;
  channel: { id: string | null; title: string | null; thumbnail: string | null; subscribers: number | null };
  videos: number;
  last_synced_at: string | null;
  last_job: SyncJob | null;
}

export interface VideoSummary {
  id: string;
  title: string;
  thumbnail_url: string | null;
  published_at: string | null;
  duration_sec: number;
  is_short: boolean;
  views: number;
  likes: number;
  comment_count: number;
  engagement_rate: number | null;
  avg_view_pct: number | null;
  avg_view_duration_s: number | null;
  subscribers_gained: number | null;
  subs_per_1k_views: number | null;
  engaged_views: number | null;
  hook_retention_pct: number | null;
  looping: boolean;
  has_retention: boolean;
  reliable: boolean;
  transcript_status: "pending" | "ok" | "none" | "error";
  description?: string;
}

export interface Medians {
  views: number | null;
  avg_view_pct: number | null;
  hook_retention_pct: number | null;
  subs_per_1k_views: number | null;
  engagement_rate: number | null;
}

export interface DashboardAction {
  kind: "weak_hook" | "best_day" | "conversation";
  video_id?: string;
  title: string;
  value: number;
  benchmark?: number;
  message: string;
}

export interface Dashboard {
  channel: { title: string | null; thumbnail: string | null; subscribers: number | null; last_synced_at: string | null };
  kpis: {
    videos: number;
    shorts: number;
    total_views: number;
    median_views: number;
    uploads_last_28d: number;
    median_avg_view_pct: number | null;
    median_hook_retention_pct: number | null;
    median_subs_per_1k_views: number | null;
    median_engagement_rate: number | null;
  };
  publish_days: { day: string; median_views: number; videos: number }[];
  top_videos: VideoSummary[];
  actions: DashboardAction[];
  last_job_status: JobStatus | null;
}

export interface CurvePoint {
  x: number;
  sec: number;
  y: number;
  benchmark: number | null;
}

export interface Segment {
  idx: number;
  start_sec: number;
  end_sec: number;
  text: string;
  retention_start_pct?: number;
  retention_end_pct?: number;
  delta_pct?: number;
  severity?: "leak" | "ok" | "gain";
}

export interface DropOff {
  at_sec: number;
  drop_pct: number;
  from_pct: number;
  to_pct: number;
  line: string | null;
}

export interface VideoDetail {
  video: VideoSummary;
  curve: CurvePoint[];
  drop_offs: DropOff[];
  segments: Segment[];
  transcript: { status: string; language: string | null; auto_generated: boolean | null };
  benchmark_videos: number;
  min_views_for_retention: number;
}

export interface ShortRow extends VideoSummary {
  first_line: string | null;
  biggest_drop_sec: number | null;
  biggest_drop_pct: number | null;
  retention_1s_pct: number | null;
  retention_end_pct: number | null;
}

export interface ShortsLab {
  shorts: ShortRow[];
  medians: Medians;
  median_curve: { x: number; y: number }[];
  min_views_for_retention: number;
  hook_seconds: number;
}

export interface CommentRow {
  id: string;
  author: string;
  text: string;
  likes: number;
  reply_count: number;
  published_at: string | null;
  video_id?: string;
  video_title?: string;
}

export interface AudienceInsights {
  summary: string;
  themes: { theme: string; demand: string; evidence: string[] }[];
  open_questions: string[];
  video_ideas: { title: string; hook: string; why: string }[];
}

export interface AskSource {
  video_id: string;
  title: string;
  type: "transcript" | "comments";
  start_sec: number;
  score: number;
  excerpt: string;
}

export interface HookReview {
  diagnosis: string;
  rewrites: { hook: string; technique: string }[];
  fix_first: string;
}
