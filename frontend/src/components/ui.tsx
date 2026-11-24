import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";

export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

export function Card({ className, children, ...rest }: ComponentProps<"section">) {
  return (
    <section className={cx("rounded-2xl border border-line bg-surface", className)} {...rest}>
      {children}
    </section>
  );
}

export function CardHeader({ title, subtitle, action }: { title: ReactNode; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5">
      <div className="min-w-0">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: ReactNode; description?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-sm text-ink-2">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <Card className="px-5 py-4">
      <p className="text-xs font-medium text-ink-3">{label}</p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums tracking-tight text-ink">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-3">{hint}</p>}
    </Card>
  );
}

type Tone = "neutral" | "brand" | "good" | "warn" | "critical";
const toneClass: Record<Tone, string> = {
  neutral: "border-line bg-surface-2 text-ink-2",
  brand: "border-brand/30 bg-brand/10 text-brand",
  good: "border-good/40 bg-good/10 text-good-ink",
  warn: "border-warn/40 bg-warn/10 text-warn",
  critical: "border-critical/40 bg-critical/10 text-critical-ink",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium", toneClass[tone], className)}>
      {children}
    </span>
  );
}

type Variant = "primary" | "secondary" | "ghost" | "danger";
const variantClass: Record<Variant, string> = {
  primary: "bg-brand text-brand-ink hover:bg-brand-strong",
  secondary: "border border-line bg-surface-2 text-ink hover:bg-surface-3",
  ghost: "text-ink-2 hover:bg-surface-2 hover:text-ink",
  danger: "border border-critical/50 bg-critical/10 text-critical-ink hover:bg-critical/20",
};

export function Button({
  variant = "secondary",
  loading,
  className,
  children,
  disabled,
  ...rest
}: ComponentProps<"button"> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variantClass[variant],
        className,
      )}
      {...rest}
    >
      {loading && <Loader2 size={15} className="animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-pulse rounded-lg bg-surface-2", className)} aria-hidden />;
}

export function LoadingBlock({ label = "Loading…", className }: { label?: string; className?: string }) {
  return (
    <div role="status" className={cx("flex items-center justify-center gap-2 py-16 text-sm text-ink-3", className)}>
      <Loader2 size={16} className="animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-3 rounded-xl border border-line bg-surface-2 p-3 text-ink-3">{icon ?? <Inbox size={20} />}</div>
      <p className="text-sm font-medium text-ink">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-ink-3">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div role="alert" className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <AlertTriangle size={20} className="mb-2 text-warn" aria-hidden />
      <p className="text-sm font-medium text-ink">Couldn&apos;t load this</p>
      <p className="mt-1 max-w-md text-sm text-ink-3">{message}</p>
      {retry && (
        <Button className="mt-4" onClick={retry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Thumb({ src, alt, short, className }: { src: string | null; alt: string; short?: boolean; className?: string }) {
  return (
    <div className={cx("relative shrink-0 overflow-hidden rounded-md bg-surface-3", short ? "aspect-[9/16] w-10" : "aspect-video w-20", className)}>
      {src && (
        // eslint-disable-next-line @next/next/no-img-element -- remote YouTube thumbnails, already sized by YouTube
        <img src={src} alt={alt} loading="lazy" className="h-full w-full object-cover" />
      )}
    </div>
  );
}

export function TextLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="font-medium text-brand hover:underline">
      {children}
    </Link>
  );
}
