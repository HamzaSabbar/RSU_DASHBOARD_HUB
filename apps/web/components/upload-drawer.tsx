"use client";

import { useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";

type UploadResult = {
  filename: string;
  file_kind: string;
  status: string;
  row_count: number | null;
  error: string | null;
};

type UploadSummary = {
  files_accepted: UploadResult[];
  files_rejected: UploadResult[];
};

async function uploadAction(formData: FormData): Promise<UploadSummary> {
  const res = await fetch("/api/boards/macro-national/upload-proxy", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Upload failed (${res.status}): ${body}`);
  }
  return (await res.json()) as UploadSummary;
}

export function UploadDrawer(): React.ReactElement {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [summary, setSummary] = useState<UploadSummary | null>(null);
  const [pending, startTransition] = useTransition();
  const inputRef = useRef<HTMLInputElement>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    if (![...form.getAll("files")].some((v) => v instanceof File && v.size > 0)) {
      return;
    }
    const result = await uploadAction(form);
    setSummary(result);
    startTransition(() => router.refresh());
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
                Déposez un ou plusieurs fichiers Excel ou CSV. Le système
                détecte le type automatiquement d&apos;après le nom et les
                colonnes.
              </p>
              <input
                ref={inputRef}
                type="file"
                name="files"
                multiple
                accept=".xlsx,.xls,.csv"
                className="block w-full text-sm file:mr-4 file:rounded-md file:border-0 file:bg-brand-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-brand-dark"
              />
              <Button type="submit" disabled={pending}>
                {pending ? "Traitement..." : "Envoyer"}
              </Button>
              {summary ? (
                <div className="space-y-3 rounded-md border border-brand-border p-3 text-xs">
                  {summary.files_accepted.length > 0 ? (
                    <div>
                      <p className="font-medium text-brand-positive">
                        Fichiers acceptés ({summary.files_accepted.length})
                      </p>
                      <ul className="mt-1 space-y-1 text-slate-700">
                        {summary.files_accepted.map((r) => (
                          <li key={r.filename}>
                            {r.filename}: {r.file_kind}
                            {r.row_count != null ? `, ${r.row_count} lignes` : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {summary.files_rejected.length > 0 ? (
                    <div>
                      <p className="font-medium text-brand-danger">
                        Fichiers rejetés ({summary.files_rejected.length})
                      </p>
                      <ul className="mt-1 space-y-1 text-slate-700">
                        {summary.files_rejected.map((r) => (
                          <li key={r.filename}>
                            {r.filename}: {r.error}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </form>
          </aside>
        </div>
      ) : null}
    </>
  );
}
