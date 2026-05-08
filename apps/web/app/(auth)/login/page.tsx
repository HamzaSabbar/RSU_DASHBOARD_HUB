import { redirect } from "next/navigation";
import { BrandMark } from "@/components/brand-mark";
import { auth } from "@/lib/auth";
import { LoginForm } from "./login-form";

export const dynamic = "force-dynamic";

export default async function LoginPage({
  searchParams,
}: {
  searchParams?: { reauth?: string };
}): Promise<React.ReactElement> {
  const session = await auth();
  if (session && searchParams?.reauth !== "1") redirect("/dashboard");

  return (
    <main className="rsu-dot-bg relative flex min-h-screen flex-col overflow-hidden text-brand-ink">
      <div className="pointer-events-none absolute right-0 top-0 h-[360px] w-[520px] bg-[radial-gradient(circle_at_70%_30%,rgba(31,138,91,0.14),transparent_55%)]" />
      <header className="relative z-10 flex h-16 items-center justify-between px-6">
        <BrandMark compact />
        <p className="hidden text-xs text-brand-muted sm:block">
          Besoin d&apos;aide ?{" "}
          <a className="font-medium text-brand-ink underline" href="mailto:support@ancs.gov.ma">
            support@ancs.gov.ma
          </a>
        </p>
      </header>

      <section className="relative z-10 flex flex-1 items-center justify-center px-6 py-10">
        <div className="w-full max-w-[460px]">
          <div className="mb-6 flex flex-col items-center text-center">
            <BrandMark className="justify-center" />
            <p className="mt-2 text-[11px] font-medium uppercase tracking-[0.22em] text-brand-muted">
              Espace authentifié
            </p>
          </div>
          <LoginForm />
        </div>
      </section>

      <footer className="relative z-10 pb-8 text-center text-xs text-brand-muted">
        (c) 2026 ANCS - Royaume du Maroc - Tous droits réservés
      </footer>
    </main>
  );
}
