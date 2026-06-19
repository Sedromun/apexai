"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth";

function LogoMark() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M7 17 L14 10" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="15.5" cy="8.5" r="1.7" fill="#fff" />
    </svg>
  );
}

function GaugeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 15a8 8 0 0 1 16 0" />
      <path d="M12 15 L15.5 10.5" />
    </svg>
  );
}

function ActivityIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 13h4l2-6 3 11 2-7h5" />
    </svg>
  );
}

function CompareIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 8h16" />
      <path d="M4 16h16" />
      <path d="M9 5 6 8l3 3" />
      <path d="M15 19l3-3-3-3" />
    </svg>
  );
}

function DiamondIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round">
      <path d="M12 3 L21 12 L12 21 L3 12 Z" />
    </svg>
  );
}

function ExitIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 4h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-3" />
      <path d="M10 8l-4 4 4 4" />
      <path d="M6 12h9" />
    </svg>
  );
}

const NAV = [
  { href: "/dashboard", label: "Дашборд", Icon: GaugeIcon },
  { href: "/laps", label: "Круги", Icon: ActivityIcon },
  { href: "/compare", label: "Сравнение", Icon: CompareIcon },
  { href: "/account", label: "Аккаунт", Icon: DiamondIcon },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const initials = (user?.email ?? "?").slice(0, 2).toUpperCase();

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-[68px] flex-col items-center gap-2 border-r border-border bg-surface/70 py-4 backdrop-blur">
        <Link
          href="/dashboard"
          title="ApexAI"
          className="mb-2 grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-[#ff2d46] to-[#ff5b73] shadow-[0_6px_20px_-6px_rgba(255,45,70,0.8)]"
        >
          <LogoMark />
        </Link>

        <nav className="flex flex-1 flex-col items-center gap-1.5">
          {NAV.map(({ href, label, Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                title={label}
                className={cn(
                  "grid h-11 w-11 place-items-center rounded-2xl transition",
                  active
                    ? "bg-primary/15 text-primary"
                    : "text-muted hover:bg-surface-2 hover:text-foreground",
                )}
              >
                <Icon />
              </Link>
            );
          })}
        </nav>

        <button
          type="button"
          onClick={() => logout()}
          title="Выйти"
          className="grid h-11 w-11 place-items-center rounded-2xl text-muted transition hover:bg-surface-2 hover:text-foreground"
        >
          <ExitIcon />
        </button>
        <div
          title={user?.email}
          className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-[#ff2d46] to-[#ff5b73] font-display text-sm font-semibold text-white"
        >
          {initials}
        </div>
      </aside>

      <main className="ml-[68px]">
        <div className="mx-auto max-w-6xl px-6 py-7">{children}</div>
      </main>
    </div>
  );
}
