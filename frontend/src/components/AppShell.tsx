"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { useState } from "react";
import { Clapperboard, LayoutDashboard, Lightbulb, LogOut, Menu, MessageSquareText, MessagesSquare, Settings, Smartphone, X } from "lucide-react";
import { Logo } from "./Logo";
import SyncButton from "./SyncButton";
import { cx } from "./ui";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/shorts", label: "Shorts Lab", icon: Smartphone },
  { href: "/videos", label: "Videos", icon: Clapperboard },
  { href: "/audience", label: "Audience", icon: MessagesSquare },
  { href: "/ideas", label: "Ideas", icon: Lightbulb },
  { href: "/ask", label: "Ask your channel", icon: MessageSquareText },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  const item = (href: string, label: string, Icon: typeof LayoutDashboard) => (
    <Link
      key={href}
      href={href}
      onClick={onNavigate}
      aria-current={isActive(href) ? "page" : undefined}
      className={cx(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
        isActive(href) ? "bg-surface-2 font-medium text-ink" : "text-ink-2 hover:bg-surface-2/60 hover:text-ink",
      )}
    >
      <Icon size={17} className={isActive(href) ? "text-brand" : "text-ink-3"} aria-hidden />
      {label}
    </Link>
  );
  return (
    <nav className="flex flex-1 flex-col gap-0.5" aria-label="Main">
      {NAV.map((n) => item(n.href, n.label, n.icon))}
      <div className="mt-auto pt-4">{item("/settings", "Settings", Settings)}</div>
    </nav>
  );
}

function UserCard() {
  const { data } = useSession();
  if (!data?.user) return null;
  return (
    <div className="flex items-center gap-3 border-t border-line px-2 pt-4">
      {data.user.image ? (
        // eslint-disable-next-line @next/next/no-img-element -- Google avatar
        <img src={data.user.image} alt="" className="h-8 w-8 rounded-full" referrerPolicy="no-referrer" />
      ) : (
        <div className="h-8 w-8 rounded-full bg-surface-3" />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">{data.user.name}</p>
        <p className="truncate text-xs text-ink-3">{data.user.email}</p>
      </div>
      <button
        onClick={() => signOut({ callbackUrl: "/login" })}
        className="rounded-md p-1.5 text-ink-3 hover:bg-surface-2 hover:text-ink"
        aria-label="Sign out"
        title="Sign out"
      >
        <LogOut size={16} />
      </button>
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [drawer, setDrawer] = useState(false);
  const { data: session } = useSession();

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-line bg-bg px-3 py-5 lg:flex">
        <Link href="/" className="mb-7 px-2">
          <Logo />
        </Link>
        <NavLinks />
        <div className="mt-4">
          <UserCard />
        </div>
      </aside>

      {drawer && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-black/60" onClick={() => setDrawer(false)} />
          <div className="absolute inset-y-0 left-0 flex w-72 flex-col border-r border-line bg-bg px-3 py-5">
            <div className="mb-7 flex items-center justify-between px-2">
              <Logo />
              <button onClick={() => setDrawer(false)} className="p-1 text-ink-3" aria-label="Close menu">
                <X size={18} />
              </button>
            </div>
            <NavLinks onNavigate={() => setDrawer(false)} />
            <div className="mt-4">
              <UserCard />
            </div>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-line bg-bg/85 px-4 backdrop-blur md:px-8">
          <button className="rounded-md p-1.5 text-ink-2 lg:hidden" onClick={() => setDrawer(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <div className="lg:hidden">
            <Logo />
          </div>
          <div className="ml-auto flex items-center gap-3">
            {session?.error === "RefreshAccessTokenError" && (
              <button onClick={() => signOut({ callbackUrl: "/login" })} className="text-xs text-warn hover:underline">
                Google session expired — sign in again
              </button>
            )}
            <SyncButton />
          </div>
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8 md:px-8">{children}</main>
      </div>
    </div>
  );
}
