import { redirect } from "next/navigation";
import { AppSidebar } from "@/components/app-sidebar";
import { auth } from "@/lib/auth";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}): Promise<React.ReactElement> {
  const session = await auth();
  if (!session) redirect("/login");
  const role = (session.user as { role?: string } | undefined)?.role;

  return (
    <div className="min-h-screen bg-brand-bg text-brand-ink">
      <AppSidebar email={session.user?.email ?? ""} role={role} />
      <main className="min-h-screen lg:pl-60">{children}</main>
    </div>
  );
}
