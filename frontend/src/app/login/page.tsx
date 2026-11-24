import type { Metadata } from "next";
import { Eye, ShieldCheck, Sparkles } from "lucide-react";
import { Logo } from "@/components/Logo";
import SignInButton from "./SignInButton";

export const metadata: Metadata = { title: "Sign in" };

function safeCallback(raw: string | string[] | undefined) {
  const value = Array.isArray(raw) ? raw[0] : raw;
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

const POINTS = [
  { icon: Eye, title: "Second-by-second retention", text: "Every line of your script mapped onto the retention curve." },
  { icon: Sparkles, title: "Hook doctor", text: "Find weak openings and get rewrites grounded in your own data." },
  { icon: ShieldCheck, title: "Read-only access", text: "We never post, edit or delete anything on your channel." },
];

export default async function LoginPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const callbackUrl = safeCallback(params.callbackUrl);
  const error = params.error;

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-between px-6 py-10 sm:px-12">
        <Logo />
        <div className="mx-auto w-full max-w-sm">
          <h1 className="text-3xl font-semibold tracking-tight text-ink">See the second your viewers leave.</h1>
          <p className="mt-3 text-ink-2">
            Retention analytics built for Shorts creators: hooks, drop-offs and what your audience is asking for next.
          </p>
          <div className="mt-8">
            <SignInButton callbackUrl={callbackUrl} />
          </div>
          {error && (
            <p role="alert" className="mt-4 rounded-lg border border-warn/40 bg-warn/10 p-3 text-sm text-warn">
              Sign-in failed. Use a Google account with a verified email that owns a YouTube channel.
            </p>
          )}
          <p className="mt-6 text-xs text-ink-3">
            Requests read-only access to YouTube and YouTube Analytics. You can delete all stored data from Settings at any time.
          </p>
        </div>
        <p className="text-xs text-ink-3">© {new Date().getFullYear()} BlindCreators</p>
      </div>

      <div className="relative hidden overflow-hidden border-l border-line bg-surface lg:flex lg:items-center lg:justify-center">
        <svg className="absolute inset-x-0 top-1/2 -translate-y-1/2 opacity-90" viewBox="0 0 600 260" aria-hidden>
          <defs>
            <linearGradient id="fade" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--color-series-1)" stopOpacity="0.28" />
              <stop offset="100%" stopColor="var(--color-series-1)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d="M0 30 C60 34 70 90 120 96 S220 104 260 110 S300 160 340 170 S470 178 600 186 L600 260 L0 260Z" fill="url(#fade)" />
          <path d="M0 30 C60 34 70 90 120 96 S220 104 260 110 S300 160 340 170 S470 178 600 186" fill="none" stroke="var(--color-series-1)" strokeWidth="2" />
          <path d="M0 50 C80 70 160 100 300 120 S500 150 600 160" fill="none" stroke="var(--color-benchmark)" strokeWidth="1.5" strokeDasharray="5 5" />
          <rect x="268" y="0" width="70" height="260" fill="var(--color-critical)" opacity="0.08" />
        </svg>
        <ul className="relative z-10 mx-12 grid max-w-md gap-4">
          {POINTS.map(({ icon: Icon, title, text }) => (
            <li key={title} className="flex gap-4 rounded-2xl border border-line bg-bg/80 p-5 backdrop-blur">
              <Icon size={20} className="mt-0.5 shrink-0 text-brand" aria-hidden />
              <div>
                <p className="font-medium text-ink">{title}</p>
                <p className="mt-1 text-sm text-ink-2">{text}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
