"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  BellRing,
  ClipboardList,
  DoorOpen,
  LayoutDashboard,
  MessageSquareWarning,
  RefreshCcw,
  ShieldCheck,
  ShieldQuestion,
} from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { ImportDataDialog } from "@/components/kpi/import-data-dialog";
import { UserMenu } from "@/app/(app)/user-menu";
import { cn } from "@/lib/utils";

const sectionLinks = [
  { href: "/dashboard/acces", label: "Accès", icon: DoorOpen },
  { href: "/dashboard/inscription", label: "Inscription", icon: ClipboardList },
  {
    href: "/dashboard/fiabilisation-sources",
    label: "Fiabilisation des sources",
    icon: ShieldCheck,
  },
  { href: "/dashboard/maj-rescoring", label: "Mise à jour & rescoring", icon: RefreshCcw },
  { href: "/dashboard/notification", label: "Notification", icon: BellRing },
  {
    href: "/dashboard/recours-reclamations",
    label: "Recours & réclamations",
    icon: MessageSquareWarning,
  },
  { href: "/dashboard/controle-qualite", label: "Contrôle qualité", icon: ShieldQuestion },
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
        <div className="flex h-14 items-center border-b border-brand-border px-4">
          <Link href="/dashboard" aria-label="RSU KPI">
            <BrandMark />
          </Link>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-4">
          <nav className="space-y-5">
            <NavGroup label="Pilotage RSU">
              <SidebarLink
                href="/dashboard"
                label="Vue d'ensemble"
                icon={LayoutDashboard}
                active={pathname === "/dashboard"}
              />
              {sectionLinks.map((item) => (
                <SidebarLink
                  key={item.href}
                  href={item.href}
                  label={item.label}
                  icon={item.icon}
                  active={pathname === item.href || pathname.startsWith(`${item.href}/`)}
                />
              ))}
            </NavGroup>

            <NavGroup label="Données">
              <ImportDataDialog />
            </NavGroup>

            {role === "admin" ? (
              <NavGroup label="Système">
                <SidebarLink
                  href="/admin"
                  label="Administration"
                  icon={Bell}
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
        <Link href="/dashboard" aria-label="RSU KPI">
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
}: {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  active?: boolean;
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
    </Link>
  );
}
