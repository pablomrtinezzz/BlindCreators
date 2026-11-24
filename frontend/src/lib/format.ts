const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("en");

export const fmtCompact = (n: number | null | undefined) => (n == null ? "—" : compact.format(n));
export const fmtNumber = (n: number | null | undefined) => (n == null ? "—" : full.format(n));
export const fmtPct = (n: number | null | undefined, digits = 0) => (n == null ? "—" : `${n.toFixed(digits)}%`);

export function fmtDuration(sec: number) {
  const s = Math.round(sec);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  if (m < 60) return `${m}:${String(r).padStart(2, "0")}`;
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

export function fmtTimestamp(sec: number) {
  const s = Math.max(0, sec);
  const m = Math.floor(s / 60);
  return `${m}:${(s % 60).toFixed(1).padStart(4, "0")}`;
}

export function fmtRelative(iso: string | null | undefined) {
  if (!iso) return "never";
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  const diff = (Date.now() - date.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} h ago`;
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} d ago`;
  return date.toLocaleDateString("en", { day: "numeric", month: "short", year: "numeric" });
}

export function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en", { day: "numeric", month: "short", year: "numeric" });
}

export const youtubeUrl = (id: string, sec?: number) =>
  `https://www.youtube.com/watch?v=${id}${sec ? `&t=${Math.floor(sec)}s` : ""}`;
