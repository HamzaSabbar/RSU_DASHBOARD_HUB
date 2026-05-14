"use client";

import * as React from "react";

type ExportDownloadButtonProps = {
  href: string;
  filename: string;
  className?: string;
  pendingLabel?: string;
  children: React.ReactNode;
};

export function ExportDownloadButton({
  href,
  filename,
  className,
  pendingLabel = "Préparation...",
  children,
}: ExportDownloadButtonProps): React.ReactElement {
  const [pending, setPending] = React.useState(false);

  async function download(): Promise<void> {
    if (pending) return;
    setPending(true);
    try {
      const response = await fetch(href, {
        credentials: "same-origin",
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(await exportErrorMessage(response));
      }

      const blob = await response.blob();
      if (blob.size === 0) {
        throw new Error("Export impossible: le serveur a retourné un fichier vide.");
      }

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
    } catch (error) {
      window.alert(
        error instanceof Error
          ? error.message
          : "Export impossible: erreur inconnue pendant le téléchargement.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      className={className}
      onClick={download}
      disabled={pending}
      aria-busy={pending}
    >
      {pending ? pendingLabel : children}
    </button>
  );
}

async function exportErrorMessage(response: Response): Promise<string> {
  let fallback = `Export impossible: erreur serveur ${response.status}.`;
  let text = "";

  try {
    text = await response.text();
    if (!text.trim()) return fallback;

    const body = JSON.parse(text) as {
      detail?: unknown;
      message?: unknown;
    };
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string") return message;
    }
    if (typeof body.message === "string") return body.message;
  } catch {
    if (text.trim()) fallback = text.trim();
  }

  return fallback;
}
