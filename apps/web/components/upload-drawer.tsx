"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
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

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function UploadDrawer(): React.ReactElement {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [reportStatus, setReportStatus] =
    useState<ReportJobStatusResponse | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [duplicate, setDuplicate] = useState<{
    idChargement: string | null;
    message: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    await submitSelectedFile(false);
  }

  async function submitSelectedFile(replace: boolean): Promise<void> {
    setError(null);
    setValidation(null);
    setDuplicate(null);

    const file = inputRef.current?.files?.[0];
    if (!file || file.size === 0) return;
    setSubmitting(true);
    try {
      const job = await uploadReportAction(file, replace);
      let latest = await getReportStatus(job.jobId);
      setReportStatus(latest);
      for (let attempt = 0; attempt < 120; attempt += 1) {
        if (latest.status === "succeeded") {
          router.push("/dashboard/macro-national");
          router.refresh();
          return;
        }
        if (latest.status === "failed") {
          setValidation(await getValidation(job.jobId));
          setError(latest.errorSummary ?? "Le traitement du rapport a échoué.");
          return;
        }
        await delay(1000);
        latest = await getReportStatus(job.jobId);
        setReportStatus(latest);
      }
      setError("Le traitement prend plus de temps que prévu. Réessayez dans quelques instants.");
    } catch (err) {
      if (err instanceof DuplicateUploadError) {
        setDuplicate({
          idChargement: err.idChargement,
          message: err.message,
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
      <Button type="button" onClick={() => setOpen(true)}>
        Charger des données
      </Button>
      {open ? (
        <div
          className="fixed inset-0 z-50 flex justify-end bg-slate-900/40"
          onClick={() => setOpen(false)}
        >
          <aside
            className="flex h-full w-full max-w-md flex-col bg-brand-surface shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between border-b border-brand-border px-6 py-4">
              <h2 className="text-base font-semibold text-brand-dark">
                Chargement des données
              </h2>
              <button
                type="button"
                className="text-brand-muted hover:text-slate-900"
                onClick={() => setOpen(false)}
              >
                <X className="h-5 w-5" />
              </button>
            </header>
            <form
              onSubmit={onSubmit}
              className="flex flex-1 flex-col gap-4 overflow-auto p-6"
            >
              <p className="text-sm text-brand-muted">
                Chargez le classeur hebdomadaire RSU complet. Le serveur crée
                un job, puis le worker valide le fichier et alimente les faits
                cumulés utilisés par le dashboard.
              </p>

              <input
                ref={inputRef}
                type="file"
                name="file"
                accept=".xlsx"
                className="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-brand-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-brand-dark"
              />

              <Button type="submit" disabled={submitting}>
                {submitting ? "Traitement..." : "Envoyer"}
              </Button>

              {duplicate ? (
                <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
                  <p className="font-medium">
                    {duplicate.idChargement
                      ? `id_chargement ${duplicate.idChargement} existe déjà`
                      : "Ce chargement existe déjà"}
                  </p>
                  <p className="mt-1">{duplicate.message}</p>
                  <Button
                    type="button"
                    size="sm"
                    className="mt-3"
                    disabled={submitting}
                    onClick={() => void submitSelectedFile(true)}
                  >
                    Remplacer la version active
                  </Button>
                </div>
              ) : null}

              {reportStatus ? (
                <div className="rounded-md border border-brand-border p-3 text-xs text-slate-700">
                  <p className="font-medium text-brand-dark">
                    Job {reportStatus.jobId}
                  </p>
                  <p className="mt-1">
                    Statut: {reportStatus.status} ({reportStatus.progress}%)
                  </p>
                </div>
              ) : null}

              {error ? (
                <div className="rounded-md bg-red-50 px-3 py-2 text-xs text-brand-danger">
                  {error}
                </div>
              ) : null}

              {validation ? (
                <div className="rounded-md border border-brand-border p-3 text-xs">
                  <p className="font-medium text-brand-danger">
                    Validation: {validation.summary.errors} erreurs,{" "}
                    {validation.summary.warnings} avertissements
                  </p>
                  <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-slate-700">
                    {validation.messages.slice(0, 8).map((message, index) => (
                      <li key={`${message.code}-${index}`}>
                        {message.sheet ? `${message.sheet}: ` : ""}
                        {message.message}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

            </form>
          </aside>
        </div>
      ) : null}
    </>
  );
}
