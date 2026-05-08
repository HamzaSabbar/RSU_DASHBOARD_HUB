"use client";

import { signOut } from "next-auth/react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

export function UserMenu({
  email,
  compact = false,
}: {
  email: string;
  compact?: boolean;
}): React.ReactElement {
  const initials = email
    .split("@")[0]
    .split(/[.\-_]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "U";

  if (compact) {
    return (
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-8 w-8 rounded-full"
        aria-label="Déconnexion"
        onClick={() => signOut({ callbackUrl: "/login" })}
      >
        <LogOut className="h-4 w-4" aria-hidden />
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-primary text-[11px] font-bold text-white">
        {initials}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-semibold text-brand-ink">
          {email.split("@")[0] || "Utilisateur"}
        </span>
        <span className="block text-[10px] text-brand-muted">Session active</span>
      </span>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-8 w-8"
        aria-label="Déconnexion"
        onClick={() => signOut({ callbackUrl: "/login" })}
      >
        <LogOut className="h-4 w-4" aria-hidden />
      </Button>
    </div>
  );
}
