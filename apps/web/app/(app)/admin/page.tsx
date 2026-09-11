import Link from "next/link";
import { redirect } from "next/navigation";
import { ChevronRight, ShieldAlert, UserPlus, Users } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import { auth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

type AdminUser = {
  id: string;
  email: string;
  role: string;
};

async function createViewer(formData: FormData): Promise<void> {
  "use server";

  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) {
    redirect("/admin?userError=missing");
  }
  if (password.length < 8) {
    redirect("/admin?userError=password");
  }

  try {
    await apiFetch<AdminUser>("/api/auth/users", {
      method: "POST",
      body: JSON.stringify({ email, password, role: "viewer" }),
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      redirect("/admin?userError=exists");
    }
    throw error;
  }

  redirect(`/admin?viewerCreated=1&email=${encodeURIComponent(email)}`);
}

export default async function AdminPage({
  searchParams,
}: {
  searchParams?: {
    viewerCreated?: string;
    email?: string;
    userError?: string;
  };
}): Promise<React.ReactElement> {
  const session = await auth();
  const role = (session?.user as { role?: string } | undefined)?.role;
  if (role !== "admin") redirect("/dashboard");
  const users = await apiFetch<AdminUser[]>("/api/auth/users");
  const viewerCount = users.filter((user) => user.role === "viewer").length;

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-5">
        <div className="flex items-center gap-2 text-xs text-brand-muted">
          <Link href="/dashboard" className="hover:text-brand-ink">
            Vue d&apos;ensemble
          </Link>
          <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          <span className="font-medium text-brand-ink">Administration</span>
        </div>
      </header>

      <div className="space-y-6 px-5 py-8">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
              <ShieldAlert className="h-4 w-4" aria-hidden />
            </span>
            <h1 className="text-2xl font-semibold text-brand-ink">Administration</h1>
          </div>
          <p className="mt-2 text-sm text-brand-muted">
            Gérez les accès en lecture seule du dashboard.
          </p>
        </div>

        {searchParams?.viewerCreated === "1" ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Lecteur créé: {searchParams.email ?? "nouvel utilisateur"}.
          </div>
        ) : null}

        {searchParams?.userError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {viewerErrorMessage(searchParams.userError)}
          </div>
        ) : null}

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="rounded-lg border border-brand-border bg-brand-surface">
            <div className="flex items-start gap-4 border-b border-brand-border p-5">
              <span className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
                <UserPlus className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <h2 className="text-base font-semibold text-brand-ink">
                  Créer un lecteur
                </h2>
                <p className="mt-2 text-sm leading-6 text-brand-muted">
                  Un lecteur peut consulter le dashboard et utiliser les filtres.
                  Il ne peut pas charger de nouvelles données.
                </p>
              </div>
            </div>

            <form action={createViewer} className="grid gap-4 p-5 md:grid-cols-2">
              <label className="block text-sm font-medium text-brand-ink">
                Email
                <input
                  name="email"
                  type="email"
                  required
                  placeholder="lecteur@exemple.ma"
                  className="mt-2 w-full rounded-md border border-brand-border px-3 py-2 text-sm text-brand-ink outline-none focus:border-brand-primary"
                />
              </label>
              <label className="block text-sm font-medium text-brand-ink">
                Mot de passe temporaire
                <input
                  name="password"
                  type="password"
                  required
                  minLength={8}
                  placeholder="8 caractères minimum"
                  className="mt-2 w-full rounded-md border border-brand-border px-3 py-2 text-sm text-brand-ink outline-none focus:border-brand-primary"
                />
              </label>
              <div className="md:col-span-2">
                <Button type="submit" className="gap-2">
                  <UserPlus className="h-4 w-4" aria-hidden />
                  Créer le lecteur
                </Button>
              </div>
            </form>
          </div>

          <div className="rounded-lg border border-brand-border bg-brand-surface">
            <div className="flex items-center justify-between border-b border-brand-border p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-bg text-brand-ink">
                  <Users className="h-4 w-4" aria-hidden />
                </span>
                <div>
                  <h2 className="text-base font-semibold text-brand-ink">Utilisateurs</h2>
                  <p className="text-xs text-brand-muted">{viewerCount} lecteur(s)</p>
                </div>
              </div>
            </div>
            <div className="divide-y divide-brand-border">
              {users.map((user) => (
                <div key={user.id} className="flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-brand-ink">{user.email}</p>
                    <p className="mt-1 text-xs text-brand-muted">{roleLabel(user.role)}</p>
                  </div>
                  <span className="rounded bg-brand-bg px-2 py-1 text-[11px] font-medium text-brand-soft">
                    {user.role}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function viewerErrorMessage(error: string): string {
  if (error === "missing") return "Email et mot de passe sont requis.";
  if (error === "password") return "Le mot de passe doit contenir au moins 8 caractères.";
  if (error === "exists") return "Un utilisateur avec cet email existe déjà.";
  return "Impossible de créer le lecteur.";
}

function roleLabel(role: string): string {
  if (role === "admin") return "Administrateur";
  if (role === "editor") return "Gestionnaire";
  return "Lecture seule";
}
