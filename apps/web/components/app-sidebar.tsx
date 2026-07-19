"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bell,
  ChevronRight,
  LayoutDashboard,
  LineChart,
  Search,
  Settings,
} from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { UserMenu } from "@/app/(app)/user-menu";
import { cn } from "@/lib/utils";

const boardLinks = [
  { href: "/dashboard/macro-national", label: "Macro National", icon: LineChart, ready: true },
  {
    href: "/dashboard/programmes-sociaux-rescoring",
    label: "Programmes sociaux",
    icon: BarChart3,
    ready: false,
  },
];

export function AppSidebar({
  email,
  role,
}: {
  email: string;
  role?: string;
}): React.ReactElement {
  const pathname = usePathname();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-brand-border bg-brand-surface lg:flex">
        <div className="flex h-14 items-center justify-between border-b border-brand-border px-4">
          <Link href="/dashboard" aria-label="RSU Dashboard Hub">
            <BrandMark />
          </Link>
          <ChevronRight className="h-4 w-4 text-brand-ink" aria-hidden />
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-brand-muted" />
            <input
              type="search"
              placeholder="Rechercher..."
              className="h-8 w-full rounded-md border border-brand-border bg-white pl-9 pr-10 text-xs text-brand-ink outline-none placeholder:text-brand-muted focus:border-brand-primary"
            />
            <span className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-brand-border px-1.5 py-0.5 text-[10px] leading-none text-brand-muted">
              K
            </span>
          </div>

          <nav className="mt-5 space-y-5">
            <NavGroup label="Espace">
              <SidebarLink
                href="/dashboard"
                label="Hub"
                icon={LayoutDashboard}
                active={pathname === "/dashboard"}
              />
            </NavGroup>

            <NavGroup label="Tableaux de bord">
              {boardLinks.map((item) => (
                <SidebarLink
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
                  ready={item.ready}
                />
              ))}
            </NavGroup>

            {role === "admin" ? (
              <NavGroup label="Système">
                <SidebarLink
                  href="/admin"
                  label="Administration"
                  icon={Settings}
                  active={pathname === "/admin"}
                />
              </NavGroup>
            ) : null}
          </nav>
        </div>

        <div className="border-t border-brand-border p-3">
          <UserMenu email={email} />
        </div>
      </aside>

      <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-4 lg:hidden">
        <Link href="/dashboard" aria-label="RSU Dashboard Hub">
          <BrandMark compact />
        </Link>
        <div className="flex items-center gap-3">
          <Bell className="h-4 w-4 text-brand-ink" aria-hidden />
          <UserMenu email={email} compact />
        </div>
      </header>
    </>
  );
}

function NavGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}): React.ReactElement {
  return (
    <div>
      <p className="px-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-brand-muted">
        {label}
      </p>
      <div className="mt-2 space-y-1">{children}</div>
    </div>
  );
}

function SidebarLink({
  href,
  label,
  icon: Icon,
  active,
  ready,
}: {
  href: string;
  label: string;
  icon: typeof BarChart3;
  active?: boolean;
  ready?: boolean;
}): React.ReactElement {
  return (
    <Link
      href={href}
      className={cn(
        "flex h-9 items-center gap-2 rounded-md px-2.5 text-sm font-medium text-brand-soft transition",
        active
          ? "border border-brand-border bg-white text-brand-ink shadow-[0_1px_2px_rgba(20,20,15,0.03)]"
          : "hover:bg-brand-bg hover:text-brand-ink",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {ready ? (
        <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-brand-primary">
          Actif
        </span>
      ) : null}
    </Link>
  );
}
