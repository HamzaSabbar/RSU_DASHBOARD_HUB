"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";

type ReportJobCreateResponse = {
  jobId: string;
  status: "queued" | "running" | "succeeded" | "failed";
  statusUrl: string;
  dashboardUrl: string;
  validationUrl: string;
};

type ReportJobStatusResponse = {
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
    section: string | null;
    row: number | null;
    column: string | null;
    code: string;
    message: string;
  }[];
};

type SelectedFile = {
  name: string;
  size: number;
  lastModified: number;
};

type UploadSuccess = {
  fileName: string;
  jobId: string;
  warnings: number;
};

type UploadConflict = {
  kind: "duplicate" | "overlap";
  idChargement: string | null;
  message: string;
  confirming: boolean;
};

class DuplicateUploadError extends Error {
  constructor(
    message: string,
    public readonly idChargement: string | null,
  ) {
    super(message);
  }
}

async function uploadReportAction(
  file: File,
  replace: boolean,
): Promise<ReportJobCreateResponse> {
  const formData = new FormData();
  formData.set("file", file);
  const res = await fetch(`/api/reports/jobs?replace=${replace ? "true" : "false"}`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw await responseError(res);
  }
  return (await res.json()) as ReportJobCreateResponse;
}

async function getReportStatus(jobId: string): Promise<ReportJobStatusResponse> {
  const res = await fetch(`/api/reports/jobs/${jobId}/status`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw await responseError(res);
  }
  return (await res.json()) as ReportJobStatusResponse;
}

async function getValidation(jobId: string): Promise<ValidationResult | null> {
  const res = await fetch(`/api/reports/jobs/${jobId}/validation`, {
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as ValidationResult;
}

async function responseError(res: Response): Promise<Error> {
  const text = await res.text();
  try {
    const parsed = JSON.parse(text) as { detail?: unknown };
    if (isDuplicateDetail(parsed.detail)) {
      return new DuplicateUploadError(parsed.detail.message, parsed.detail.idChargement);
    }
    if (typeof parsed.detail === "string") return new Error(parsed.detail);
    if (isMessageDetail(parsed.detail)) return new Error(parsed.detail.message);
  } catch {
    // keep raw text
  }
  return new Error(`Upload failed (${res.status}): ${text}`);
}

function isDuplicateDetail(
  detail: unknown,
): detail is { code: string; idChargement: string | null; message: string } {
  return (
    typeof detail === "object" &&
    detail !== null &&
    "code" in detail &&
    (detail as { code?: unknown }).code === "DUPLICATE_ID_CHARGEMENT" &&
    typeof (detail as { message?: unknown }).message === "string"
  );
}

function isMessageDetail(detail: unknown): detail is { message: string } {
  return (
    typeof detail === "object" &&
    detail !== null &&
    typeof (detail as { message?: unknown }).message === "string"
  );
}

function isOverlapError(message: string | null | undefined): boolean {
  return Boolean(message?.toLowerCase().includes("chevauchante"));
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function UploadDrawer(): React.ReactElement {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [reportStatus, setReportStatus] =
    useState<ReportJobStatusResponse | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [success, setSuccess] = useState<UploadSuccess | null>(null);
  const [conflict, setConflict] = useState<UploadConflict | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    await submitSelectedFile(false);
  }

  function onFileChange(event: React.ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(
      file
        ? {
            name: file.name,
            size: file.size,
            lastModified: file.lastModified,
          }
        : null,
    );
    setError(null);
    setValidation(null);
    setConflict(null);
    setSuccess(null);
    setReportStatus(null);
  }

  function clearSelectedFile(): void {
    if (inputRef.current) inputRef.current.value = "";
    setSelectedFile(null);
    setError(null);
    setValidation(null);
    setConflict(null);
    setSuccess(null);
    setReportStatus(null);
  }

  async function submitSelectedFile(replace: boolean): Promise<void> {
    setError(null);
    setValidation(null);
    setConflict(null);
    setSuccess(null);

    const file = inputRef.current?.files?.[0];
    if (!file || file.size === 0) {
      setError("Sélectionnez un fichier Excel .xlsx avant d'envoyer.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".xlsx")) {
      setError("Format invalide: le fichier doit être un .xlsx.");
      return;
    }
    setSubmitting(true);
    try {
      const job = await uploadReportAction(file, replace);
      let latest = await getReportStatus(job.jobId);
      for (let attempt = 0; attempt < 120; attempt += 1) {
        setReportStatus(latest);
        if (latest.status === "succeeded") {
          const validationResult = await getValidation(job.jobId);
          setValidation(validationResult);
          setSuccess({
            fileName: file.name,
            jobId: job.jobId,
            warnings: validationResult?.summary.warnings ?? 0,
          });
          router.refresh();
          return;
        }
        if (latest.status === "failed") {
          setValidation(await getValidation(job.jobId));
          const summary = latest.errorSummary ?? "Le traitement du rapport a échoué.";
          if (isOverlapError(summary)) {
            setConflict({
              kind: "overlap",
              idChargement: null,
              message: summary,
              confirming: false,
            });
          } else {
            setError(summary);
          }
          return;
        }
        await delay(1000);
        latest = await getReportStatus(job.jobId);
        setReportStatus(latest);
      }
      setError("Le traitement prend plus de temps que prévu. Réessayez dans quelques instants.");
    } catch (err) {
      if (err instanceof DuplicateUploadError) {
        setConflict({
          kind: "duplicate",
          idChargement: err.idChargement,
          message: err.message,
          confirming: false,
        });
      } else {
        setError(err instanceof Error ? err.message : "Upload impossible.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button
        type="button"
        size="sm"
        className="h-8 gap-2 px-3 text-xs"
        onClick={() => setOpen(true)}
      >
        <Upload className="h-3.5 w-3.5" aria-hidden />
        Charger
      </Button>
      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-brand-ink/35 p-4"
          onClick={() => {
            if (!submitting) setOpen(false);
          }}
        >
          <aside
            className="flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-xl border border-brand-border bg-brand-surface shadow-[0_24px_80px_rgba(20,20,15,0.22)]"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between gap-4 border-b border-brand-border px-6 py-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-brand-muted">
                  Nouveau chargement
                </p>
                <h2 className="mt-1 text-lg font-semibold text-brand-ink">
                  Chargement des données
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href="/api/reports/template.xlsx"
                  className="inline-flex h-8 items-center justify-center gap-2 rounded-md border border-brand-border bg-white px-3 text-xs font-medium text-brand-ink hover:bg-brand-bg"
                >
                  <Download className="h-3.5 w-3.5" aria-hidden />
                  Modèle Excel
                </a>
                <button
                  type="button"
                  className="rounded-md p-1 text-brand-muted hover:bg-brand-bg hover:text-brand-ink disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={submitting}
                  onClick={() => setOpen(false)}
                  aria-label="Fermer"
                >
                  <X className="h-5 w-5" aria-hidden />
                </button>
              </div>
            </header>
            <form
              onSubmit={onSubmit}
              className="flex flex-1 flex-col gap-4 overflow-auto p-6"
            >
              <p className="text-sm text-brand-muted">
                Chargez le classeur quotidien RSU complet. Le serveur valide le
                fichier, alimente les faits cumulés, puis rafraîchit le
                dashboard.
              </p>

              <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-brand-border-strong bg-brand-bg px-6 py-8 text-center transition hover:border-brand-primary hover:bg-white">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-brand-primary">
                  <FileSpreadsheet className="h-6 w-6" aria-hidden />
                </span>
                <span className="mt-3 text-sm font-semibold text-brand-ink">
                  {selectedFile
                    ? "Changer de fichier Excel"
                    : "Sélectionner un classeur Excel"}
                </span>
                <span className="mt-1 text-xs text-brand-muted">
                  Format attendu: .xlsx
                </span>
                <input
                  ref={inputRef}
                  type="file"
                  name="file"
                  accept=".xlsx"
                  disabled={submitting}
                  onChange={onFileChange}
                  className="sr-only"
                />
              </label>

              {selectedFile ? (
                <div className="flex items-center justify-between gap-3 rounded-lg border border-brand-border bg-white p-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
                      <FileSpreadsheet className="h-5 w-5" aria-hidden />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-brand-ink">
                        {selectedFile.name}
                      </p>
                      <p className="text-xs text-brand-muted">
                        {formatBytes(selectedFile.size)} · modifié le{" "}
                        {formatDateTime(selectedFile.lastModified)}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-brand-muted hover:bg-brand-bg hover:text-brand-ink disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={submitting}
                    onClick={clearSelectedFile}
                  >
                    Retirer
                  </button>
                </div>
              ) : null}

              <Button
                type="submit"
                className="gap-2"
                disabled={submitting || !selectedFile}
              >
                <Upload className="h-4 w-4" aria-hidden />
                {submitting ? "Traitement..." : "Envoyer le fichier"}
              </Button>

              {success ? (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-brand-primary" aria-hidden />
                    <div>
                      <p className="font-semibold">
                        Fichier chargé et dashboard mis à jour
                      </p>
                      <p className="mt-1 text-xs text-emerald-900">
                        {success.fileName} · job {success.jobId}
                        {success.warnings > 0
                          ? ` · ${success.warnings} avertissement(s)`
                          : ""}
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}

              {conflict ? (
                <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-xs text-amber-900">
                  <p className="font-medium">
                    {conflict.kind === "overlap"
                      ? "Période déjà couverte par des données actives"
                      : conflict.idChargement
                        ? `id_chargement ${conflict.idChargement} existe déjà`
                        : "Ce chargement existe déjà"}
                  </p>
                  <p className="mt-1">{conflict.message}</p>
                  {conflict.confirming ? (
                    <div className="mt-3 rounded-md border border-amber-300 bg-white p-3">
                      <p className="font-semibold text-amber-950">
                        Confirmer le remplacement des données actives ?
                      </p>
                      <p className="mt-1">
                        Les lots actifs qui chevauchent cette période seront
                        désactivés et remplacés par ce fichier.
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          disabled={submitting}
                          onClick={() => void submitSelectedFile(true)}
                        >
                          Confirmer le remplacement
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={submitting}
                          onClick={() =>
                            setConflict({ ...conflict, confirming: false })
                          }
                        >
                          Annuler
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <Button
                      type="button"
                      size="sm"
                      className="mt-3"
                      disabled={submitting}
                      onClick={() =>
                        setConflict({ ...conflict, confirming: true })
                      }
                    >
                      Remplacer les données actives
                    </Button>
                  )}
                </div>
              ) : null}

              {reportStatus ? (
                <div className="rounded-lg border border-brand-border bg-white p-4 text-xs text-brand-soft">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-brand-ink">
                        {statusLabel(reportStatus.status)}
                      </p>
                      <p className="mt-1">
                        Job {reportStatus.jobId} · {reportStatus.progress}%
                      </p>
                    </div>
                    {reportStatus.status === "succeeded" ? (
                      <CheckCircle2 className="h-5 w-5 text-brand-primary" aria-hidden />
                    ) : reportStatus.status === "failed" ? (
                      <AlertTriangle className="h-5 w-5 text-brand-danger" aria-hidden />
                    ) : (
                      <Loader2 className="h-5 w-5 animate-spin text-brand-primary" aria-hidden />
                    )}
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-brand-bg">
                    <div
                      className="h-full rounded-full bg-brand-primary transition-all"
                      style={{
                        width: `${Math.max(0, Math.min(100, reportStatus.progress))}%`,
                      }}
                    />
                  </div>
                </div>
              ) : null}

              {error ? (
                <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-xs text-brand-danger">
                  {error}
                </div>
              ) : null}

              {validation ? (
                <div className="rounded-lg border border-brand-border bg-white p-4 text-xs">
                  <p
                    className={
                      validation.summary.errors > 0
                        ? "font-semibold text-brand-danger"
                        : "font-semibold text-brand-ink"
                    }
                  >
                    Validation: {validation.summary.errors} erreur(s),{" "}
                    {validation.summary.warnings} avertissement(s)
                  </p>
                  {validation.messages.length ? (
                    <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-slate-700">
                      {validation.messages.slice(0, 8).map((message, index) => (
                        <li key={`${message.code}-${index}`}>
                          {message.sheet ? `${message.sheet}: ` : ""}
                          {message.row ? `ligne ${message.row}: ` : ""}
                          {message.message}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-brand-muted">
                      Aucun problème de validation détecté.
                    </p>
                  )}
                </div>
              ) : null}

            </form>
          </aside>
        </div>
      ) : null}
    </>
  );
}

function statusLabel(status: ReportJobStatusResponse["status"]): string {
  switch (status) {
    case "queued":
      return "En attente de traitement";
    case "running":
      return "Validation et ingestion en cours";
    case "succeeded":
      return "Traitement terminé";
    case "failed":
      return "Traitement échoué";
  }
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} o`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} Ko`;
  return `${(value / (1024 * 1024)).toFixed(1)} Mo`;
}

function formatDateTime(value: number): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
