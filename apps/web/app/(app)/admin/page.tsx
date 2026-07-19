import Link from "next/link";
import { redirect } from "next/navigation";
import {
  ChevronRight,
  Database,
  DatabaseZap,
  Play,
  ShieldAlert,
  UserPlus,
  Users,
} from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api";
import { auth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

type ClearResponse = {
  status: string;
  deleted: {
    reportJobs: number;
    uploadBatches: number;
    legacyUploads: number;
    boardSnapshots: number;
    factRows: number;
  };
};

type AdminUser = {
  id: string;
  email: string;
  role: string;
};

type DataPlatformBatch = {
  id: string;
  source_key: string;
  pipeline_version: string;
  content_hash: string | null;
  status: string;
  stage: string;
  progress: number;
  created_at: string;
  finished_at: string | null;
  error_summary: string | null;
};

async function queueRsuBuild(formData: FormData): Promise<void> {
  "use server";

  const includeScoreVariables = formData.get("includeScoreVariables") === "on";
  const batch = await apiFetch<DataPlatformBatch>("/api/data-platform/batches", {
    method: "POST",
    body: JSON.stringify({
      source_key: "rsu-csv",
      compatibility_profile: "julia-30d-v1",
      include_score_variables: includeScoreVariables,
    }),
  });
  redirect(`/admin?analyticsQueued=1&analyticsBatch=${batch.id}`);
}

async function clearReportData(formData: FormData): Promise<void> {
  "use server";

  const confirmation = String(formData.get("confirmation") ?? "");
  if (confirmation !== "CLEAR") {
    redirect("/admin?error=confirmation");
  }

  const result = await apiFetch<ClearResponse>("/api/reports/admin/data", {
    method: "DELETE",
  });
  const deleted = result.deleted;
  redirect(
    `/admin?cleared=1&jobs=${deleted.reportJobs}&batches=${deleted.uploadBatches}&facts=${deleted.factRows}`,
  );
}

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
    cleared?: string;
    jobs?: string;
    batches?: string;
    facts?: string;
    error?: string;
    viewerCreated?: string;
    email?: string;
    userError?: string;
    analyticsQueued?: string;
    analyticsBatch?: string;
  };
}): Promise<React.ReactElement> {
  const session = await auth();
  const role = (session?.user as { role?: string } | undefined)?.role;
  if (role !== "admin") redirect("/dashboard");
  const users = await apiFetch<AdminUser[]>("/api/auth/users");
  const analyticsBatches = await apiFetch<DataPlatformBatch[]>(
    "/api/data-platform/batches?limit=10",
  );
  const viewerCount = users.filter((user) => user.role === "viewer").length;

  return (
    <div className="min-h-screen bg-brand-bg">
      <header className="flex h-14 items-center justify-between border-b border-brand-border bg-brand-surface px-5">
        <div className="flex items-center gap-2 text-xs text-brand-muted">
          <Link href="/dashboard" className="hover:text-brand-ink">
            Hub
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
            Gérez les accès en lecture seule et les opérations sensibles.
          </p>
        </div>

        {searchParams?.viewerCreated === "1" ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Lecteur créé: {searchParams.email ?? "nouvel utilisateur"}.
          </div>
        ) : null}

        {searchParams?.analyticsQueued === "1" ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Préparation analytique mise en file d’attente : {searchParams.analyticsBatch}.
            Le dashboard actif ne changera qu’après validation complète.
          </div>
        ) : null}

        <section className="rounded-lg border border-brand-border bg-brand-surface">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-brand-border p-5">
            <div className="flex items-start gap-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
                <Database className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <h2 className="text-base font-semibold text-brand-ink">Plateforme de données RSU</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-brand-muted">
                  Lance la validation du dossier RAW monté en lecture seule, puis construit les tables Parquet/Arrow et le catalogue DuckDB. PostgreSQL conserve l’historique, les contrôles qualité et la version active.
                </p>
              </div>
            </div>
            <form action={queueRsuBuild} className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-brand-muted">
                <input name="includeScoreVariables" type="checkbox" defaultChecked className="h-4 w-4 accent-brand-primary" />
                Inclure score_variable.csv (traitement long)
              </label>
              <Button type="submit" className="gap-2">
                <Play className="h-4 w-4" aria-hidden />
                Préparer et publier
              </Button>
            </form>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-brand-bg text-left text-xs uppercase tracking-wide text-brand-muted">
                  <th className="px-4 py-3">Créé</th>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">Étape</th>
                  <th className="px-4 py-3">Progression</th>
                  <th className="px-4 py-3">Résultat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-border">
                {analyticsBatches.map((batch) => (
                  <tr key={batch.id}>
                    <td className="whitespace-nowrap px-4 py-3 text-brand-soft">{formatDateTime(batch.created_at)}</td>
                    <td className="px-4 py-3 font-mono text-xs text-brand-ink">{batch.content_hash?.slice(0, 12) ?? batch.id.slice(0, 8)}</td>
                    <td className="px-4 py-3 text-brand-soft">{batch.stage}</td>
                    <td className="min-w-44 px-4 py-3">
                      <div className="h-2 overflow-hidden rounded bg-brand-bg"><div className="h-full bg-brand-primary" style={{ width: `${batch.progress}%` }} /></div>
                      <span className="mt-1 block text-xs text-brand-muted">{batch.progress}%</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded px-2 py-1 text-xs font-semibold ${batch.status === "succeeded" ? "bg-green-50 text-green-800" : batch.status === "failed" ? "bg-red-50 text-red-800" : "bg-amber-50 text-amber-800"}`}>
                        {batch.status}
                      </span>
                      {batch.error_summary ? <p className="mt-2 max-w-md text-xs text-red-700">{batch.error_summary}</p> : null}
                    </td>
                  </tr>
                ))}
                {analyticsBatches.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-6 text-center text-sm text-brand-muted">Aucune préparation analytique lancée.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        {searchParams?.userError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {viewerErrorMessage(searchParams.userError)}
          </div>
        ) : null}

        {searchParams?.cleared === "1" ? (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
            Données supprimées: {searchParams.facts ?? "0"} faits,{" "}
            {searchParams.batches ?? "0"} lots, {searchParams.jobs ?? "0"} jobs.
          </div>
        ) : null}

        {searchParams?.error === "confirmation" ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            Saisissez CLEAR exactement avant de supprimer les données.
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
                  Un lecteur peut consulter le dashboard et utiliser le filtre de dates.
                  Il ne peut pas charger, remplacer, exporter ou supprimer des données.
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

        <section className="max-w-3xl rounded-lg border border-brand-border bg-brand-surface">
          <div className="flex items-start gap-4 border-b border-brand-border p-5">
            <span className="flex h-10 w-10 items-center justify-center rounded-md bg-red-50 text-brand-danger">
              <DatabaseZap className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h2 className="text-base font-semibold text-brand-ink">Clear report data</h2>
              <p className="mt-2 text-sm leading-6 text-brand-muted">
                This removes report jobs, active upload batches, dashboard snapshots, and all
                report fact rows from the database. Users and board configuration are kept.
              </p>
            </div>
          </div>

          <form action={clearReportData} className="space-y-4 p-5">
            <label className="block text-sm font-medium text-brand-ink">
              Confirmation
              <input
                name="confirmation"
                placeholder="Type CLEAR"
                className="mt-2 w-full rounded-md border border-brand-border px-3 py-2 text-sm text-brand-ink outline-none focus:border-brand-primary"
              />
            </label>
            <Button type="submit" variant="destructive">
              Clear data
            </Button>
          </form>
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

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
