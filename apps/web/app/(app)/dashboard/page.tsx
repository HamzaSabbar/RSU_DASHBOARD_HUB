import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type BoardSummary = {
  slug: string;
  title: string;
  description: string;
  last_updated: string | null;
  status: "ready" | "no_data";
};

export const dynamic = "force-dynamic";

export default async function DashboardHub(): Promise<React.ReactElement> {
  const boards = await apiFetch<BoardSummary[]>("/api/boards");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-brand-dark">
          Tableaux de bord
        </h1>
        <p className="mt-1 text-sm text-brand-muted">
          Sélectionnez un tableau pour consulter les indicateurs.
        </p>
      </div>

      {boards.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-brand-muted">
            Aucun tableau disponible pour le moment.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {boards.map((board) => (
            <Card key={board.slug} className="flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <CardTitle>{board.title}</CardTitle>
                  <Badge variant={board.status === "ready" ? "ready" : "empty"}>
                    {board.status === "ready"
                      ? "Prêt"
                      : "Aucune donnée"}
                  </Badge>
                </div>
                <CardDescription>{board.description}</CardDescription>
              </CardHeader>
              <CardContent className="mt-auto flex items-center justify-between">
                <span className="text-xs text-brand-muted">
                  {board.last_updated
                    ? `Mis à jour le ${new Date(board.last_updated).toLocaleDateString("fr-FR")}`
                    : "Aucune mise à jour"}
                </span>
                <Link
                  href={`/dashboard/${board.slug}`}
                  className="inline-flex h-9 items-center justify-center rounded-md border border-brand-border px-3 text-sm font-medium hover:bg-slate-50"
                >
                  Consulter
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
