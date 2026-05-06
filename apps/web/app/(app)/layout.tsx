import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { UserMenu } from "./user-menu";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}): Promise<React.ReactElement> {
  const session = await auth();
  if (!session) redirect("/login");
  const role = (session.user as { role?: string } | undefined)?.role;

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="border-b border-brand-border bg-brand-surface">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-brand-primary" aria-hidden />
            <span className="text-sm font-semibold text-brand-dark">
              RSU Dashboard Hub
            </span>
          </Link>
          <div className="flex items-center gap-4">
            {role === "admin" ? (
              <Link
                href="/admin"
                className="text-sm font-medium text-brand-muted transition hover:text-brand-dark"
              >
                Admin
              </Link>
            ) : null}
            <UserMenu email={session.user?.email ?? ""} />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
    </div>
  );
}
