"use client";

import { signOut } from "next-auth/react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";

export function UserMenu({ email }: { email: string }): React.ReactElement {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-brand-muted">{email}</span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => signOut({ callbackUrl: "/login" })}
      >
        <LogOut className="mr-1 h-4 w-4" />
        Déconnexion
      </Button>
    </div>
  );
}
