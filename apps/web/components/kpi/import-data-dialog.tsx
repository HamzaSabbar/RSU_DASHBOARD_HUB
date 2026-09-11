"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Upload,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ImportPreview } from "@/lib/kpi-types";

type SelectedFile = { name: string; size: number };

async function postFile(url: string, file: File): Promise<ImportPreview> {
  const formData = new FormData();
  formData.set("file", file);
  const res = await fetch(url, { method: "POST", body: formData });
  const body = (await res.json()) as ImportPreview | { detail?: unknown };
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail;
    if (detail && typeof detail === "object" && "errors" in (detail as object)) {
      return detail as ImportPreview;
    }
    throw new Error(
      typeof detail === "string" ? detail : `Échec de la requête (${res.status}).`,
    );
  }
  return body as ImportPreview;
}

export function ImportDataDialog(): React.ReactElement {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [validating, setValidating] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [committed, setCommitted] = useState<ImportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function reset(): void {
    setPreview(null);
    setCommitted(null);
    setError(null);
  }

  function close(): void {
    if (validating || committing) return;
    setOpen(false);
    reset();
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0] ?? null;
    reset();
    if (!file) {
      setSelectedFile(null);
      return;
    }
    setSelectedFile({ name: file.name, size: file.size });
    if (!file.name.toLowerCase().endsWith(".xlsx")) {
      setError("Format invalide : le fichier doit être un .xlsx.");
      return;
    }
    setValidating(true);
    try {
      const result = await postFile("/api/kpi/imports/validate", file);
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation impossible.");
    } finally {
      setValidating(false);
    }
  }

  async function onConfirm(): Promise<void> {
    const file = inputRef.current?.files?.[0];
    if (!file) return;
    setCommitting(true);
    setError(null);
    try {
      const result = await postFile("/api/kpi/imports", file);
      setCommitted(result);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import impossible.");
    } finally {
      setCommitting(false);
    }
  }

  const busy = validating || committing;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex h-9 w-full items-center gap-2 rounded-md border border-brand-border bg-white px-2.5 text-sm font-medium text-brand-soft transition hover:bg-brand-bg hover:text-brand-ink"
      >
        <Upload className="h-4 w-4 shrink-0" aria-hidden />
        Ajouter des données
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-brand-ink/35 p-4"
          onClick={close}
        >
          <div
            className="flex max-h-[92vh] w-full max-w-xl flex-col overflow-hidden rounded-xl border border-brand-border bg-brand-surface shadow-[0_24px_80px_rgba(20,20,15,0.22)]"
            onClick={(e) => e.stopPropagation()}
          >
            <header className="flex items-center justify-between gap-4 border-b border-brand-border px-6 py-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-brand-muted">
                  Ajouter des données
                </p>
                <h2 className="mt-1 text-lg font-semibold text-brand-ink">
                  Import du classeur KPI RSU
                </h2>
              </div>
              <button
                type="button"
                className="rounded-md p-1 text-brand-muted hover:bg-brand-bg hover:text-brand-ink disabled:cursor-not-allowed disabled:opacity-50"
                disabled={busy}
                onClick={close}
                aria-label="Fermer"
              >
                <X className="h-5 w-5" aria-hidden />
              </button>
            </header>

            <div className="flex flex-1 flex-col gap-4 overflow-auto p-6">
              <p className="text-sm text-brand-muted">
                Chargez un classeur Excel (.xlsx) contenant une ou plusieurs feuilles KPI.
                Le fichier est validé avant tout enregistrement — aucune donnée n&apos;est
                modifiée tant que vous n&apos;avez pas confirmé.
              </p>

              <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-brand-border-strong bg-brand-bg px-6 py-8 text-center transition hover:border-brand-primary hover:bg-white">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-brand-primary">
                  <FileSpreadsheet className="h-6 w-6" aria-hidden />
                </span>
                <span className="mt-3 text-sm font-semibold text-brand-ink">
                  {selectedFile ? "Changer de fichier Excel" : "Sélectionner un classeur Excel"}
                </span>
                <span className="mt-1 text-xs text-brand-muted">Format attendu : .xlsx</span>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".xlsx"
                  disabled={busy}
                  onChange={(e) => void onFileChange(e)}
                  className="sr-only"
                />
              </label>

              {selectedFile ? (
                <div className="flex items-center gap-3 rounded-lg border border-brand-border bg-white p-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-brand-primary">
                    <FileSpreadsheet className="h-5 w-5" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-brand-ink">
                      {selectedFile.name}
                    </p>
                    <p className="text-xs text-brand-muted">{formatBytes(selectedFile.size)}</p>
                  </div>
                  {validating ? (
                    <Loader2 className="ml-auto h-4 w-4 animate-spin text-brand-primary" aria-hidden />
                  ) : null}
                </div>
              ) : null}

              {error ? (
                <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-xs text-brand-danger">
                  {error}
                </div>
              ) : null}

              {preview ? <PreviewSummary preview={preview} /> : null}

              {committed ? (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-brand-primary" aria-hidden />
                    <div>
                      <p className="font-semibold">
                        {committed.already_committed
                          ? "Ce fichier a déjà été importé"
                          : "Import confirmé et dashboard mis à jour"}
                      </p>
                      <p className="mt-1 text-xs text-emerald-900">
                        {committed.rows_new} nouvelle(s) ligne(s) · {committed.rows_updated}{" "}
                        mise(s) à jour · {committed.rows_unchanged} inchangée(s)
                      </p>
                    </div>
                  </div>
                </div>
              ) : preview && preview.valid ? (
                <Button
                  type="button"
                  className="gap-2"
                  disabled={committing}
                  onClick={() => void onConfirm()}
                >
                  <Upload className="h-4 w-4" aria-hidden />
                  {committing ? "Enregistrement..." : "Confirmer l'import"}
                </Button>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

function PreviewSummary({ preview }: { preview: ImportPreview }): React.ReactElement {
  const allIssues = Object.values(preview.per_kpi)
    .flat()
    .flatMap((t) => [...t.errors, ...t.warnings]);

  return (
    <div className="rounded-lg border border-brand-border bg-white p-4 text-xs">
      <div className="flex items-center gap-2">
        {preview.valid ? (
          <CheckCircle2 className="h-4 w-4 text-brand-primary" aria-hidden />
        ) : (
          <AlertTriangle className="h-4 w-4 text-brand-danger" aria-hidden />
        )}
        <p className={preview.valid ? "font-semibold text-brand-ink" : "font-semibold text-brand-danger"}>
          {preview.valid ? "Fichier valide" : "Fichier invalide"} · mode {preview.mode}
        </p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-brand-soft sm:grid-cols-4">
        <Stat label="Feuilles reconnues" value={preview.recognized_sheets.length} />
        <Stat label="Lignes lues" value={preview.rows_read} />
        <Stat label="Nouvelles" value={preview.rows_new} />
        <Stat label="Mises à jour" value={preview.rows_updated} />
        <Stat label="Inchangées" value={preview.rows_unchanged} />
        <Stat label="Erreurs" value={preview.errors.length} />
        <Stat label="Avertissements" value={preview.warnings.length} />
      </div>

      {preview.missing_sheets.length > 0 ? (
        <p className="mt-2 text-brand-danger">
          Feuilles manquantes (import de référence) : {preview.missing_sheets.join(", ")}
        </p>
      ) : null}
      {preview.unknown_sheets.length > 0 ? (
        <p className="mt-2 text-amber-700">
          Feuilles non reconnues ignorées : {preview.unknown_sheets.join(", ")}
        </p>
      ) : null}
      {preview.period_min && preview.period_max ? (
        <p className="mt-2 text-brand-muted">
          Période couverte : {preview.period_min} → {preview.period_max}
        </p>
      ) : null}

      {allIssues.length > 0 ? (
        <ul className="mt-3 max-h-40 space-y-1 overflow-auto border-t border-brand-border pt-2 text-slate-700">
          {allIssues.slice(0, 10).map((issue, index) => (
            <li key={`${issue.code}-${index}`}>
              <span className={issue.severity === "error" ? "text-brand-danger" : "text-amber-700"}>
                {issue.sheet}
              </span>
              {issue.row ? ` · ligne ${issue.row}` : ""}
              {issue.column ? ` · ${issue.column}` : ""} : {issue.message}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }): React.ReactElement {
  return (
    <span>
      <span className="block font-semibold text-brand-ink">{value}</span>
      <span className="text-brand-muted">{label}</span>
    </span>
  );
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} o`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} Ko`;
  return `${(value / (1024 * 1024)).toFixed(1)} Mo`;
}
