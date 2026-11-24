export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <rect width="32" height="32" rx="8" fill="var(--color-brand-ink)" />
      <path
        d="M4 16c3.2-5.6 7.3-8.4 12-8.4S24.8 10.4 28 16c-3.2 5.6-7.3 8.4-12 8.4S7.2 21.6 4 16Z"
        fill="none"
        stroke="var(--color-brand)"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <path d="M13.5 12.2v7.6l6.4-3.8-6.4-3.8Z" fill="var(--color-brand)" />
    </svg>
  );
}

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="text-[15px] font-semibold tracking-tight text-ink">
        Blind<span className="text-brand">Creators</span>
      </span>
    </span>
  );
}
