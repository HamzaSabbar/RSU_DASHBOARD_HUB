import Link from "next/link";
import { apiFetch } from "@/lib/api";
import {
  ReportDashboardView,
  type ReportDashboard,
} from "@/components/report-dashboard-view";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type ReportJobStatus = {
  jobId: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  errorSummary: string | null;
};

type ValidationResult = {
  summary: {
    errors: number;
    warnings: number;
    infos: number;
  };
  messages: {
    severity: "error" | "warning" | "info";
    sheet: string | null;
    message: string;
  }[];
};

export const dynamic = "force-dynamic";

export default async function ReportDashboardPage({
  params,
}: {
  params: { jobId: string };
}): Promise<React.ReactElement> {
  const status = await apiFetch<ReportJobStatus>(
    `/api/reports/jobs/${params.jobId}/status`,
  );

  if (status.status !== "succeeded") {
    const validation =
      status.status === "failed"
        ? await apiFetch<ValidationResult>(
            `/api/reports/jobs/${params.jobId}/validation`,
          )
        : null;
    return <ReportStatus status={status} validation={validation} />;
  }

  const dashboard = await apiFetch<ReportDashboard>(
    `/api/reports/jobs/${params.jobId}/dashboard`,
  );

  return (
    <div className="space-y-4">
      <Link
        href="/dashboard/macro-national"
        className="text-sm text-brand-muted hover:text-brand-dark"
      >
        Retour au tableau Macro National
      </Link>
      <ReportDashboardView dashboard={dashboard} />
    </div>
  );
}

function ReportStatus({
  status,
  validation,
}: {
  status: ReportJobStatus;
  validation: ValidationResult | null;
}): React.ReactElement {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Traitement du rapport</CardTitle>
          <CardDescription>
            Job {status.jobId} · {status.status} · {status.progress}%
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-brand-muted">
          {status.errorSummary ? (
            <p className="text-brand-danger">{status.errorSummary}</p>
          ) : (
            <p>Le rapport est en cours de traitement.</p>
          )}
          <Link
            href={`/dashboard/reports/${status.jobId}`}
            className="inline-flex h-9 items-center justify-center rounded-md border border-brand-border px-3 text-sm font-medium hover:bg-slate-50"
          >
            Actualiser
          </Link>
        </CardContent>
      </Card>

      {validation ? (
        <Card>
          <CardHeader>
            <CardTitle>Validation</CardTitle>
            <CardDescription>
              {validation.summary.errors} erreurs · {validation.summary.warnings} avertissements
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-brand-muted">
              {validation.messages.slice(0, 20).map((message, index) => (
                <li key={`${message.severity}-${message.sheet}-${index}`}>
                  {message.sheet ? `${message.sheet}: ` : ""}
                  {message.message}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
