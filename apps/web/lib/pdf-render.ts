import type { NextRequest } from "next/server";
import { chromium } from "playwright";
import type { DashboardChartId } from "@/lib/dashboard-export";

type RenderOptions = {
  chartId?: DashboardChartId;
};

export class PdfRenderError extends Error {
  constructor(
    message: string,
    public readonly cause?: unknown,
  ) {
    super(message);
    this.name = "PdfRenderError";
  }
}

export async function renderDashboardPdf(
  req: NextRequest,
  options: RenderOptions = {},
): Promise<Buffer> {
  const target = printUrl(req, options.chartId);
  const browser = await launchBrowser();
  try {
    const context = await browser.newContext({
      viewport: options.chartId
        ? { width: 1122, height: 794 }
        : { width: 794, height: 1122 },
      deviceScaleFactor: 1,
      extraHTTPHeaders: renderHeaders(req),
    });
    const page = await context.newPage();
    const response = await page.goto(target.toString(), {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    if (!response?.ok()) {
      throw new Error(`Print route returned ${response?.status() ?? "no response"}`);
    }
    assertNotLoginPage(page.url());
    await page.waitForSelector('[data-export-ready="true"]', { timeout: 30_000 });
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => undefined);
    await page.emulateMedia({ media: "print" });
    await page.waitForTimeout(800);
    return await page.pdf({
      format: "A4",
      landscape: Boolean(options.chartId),
      printBackground: true,
      margin: options.chartId
        ? { top: "12mm", right: "10mm", bottom: "12mm", left: "10mm" }
        : { top: "0", right: "0", bottom: "0", left: "0" },
    });
  } catch (error) {
    throw normalizePdfError(error, target);
  } finally {
    await browser.close();
  }
}

export async function renderDashboardChartPng(
  req: NextRequest,
  chartId: DashboardChartId,
): Promise<Buffer> {
  const target = printUrl(req, chartId);
  const browser = await launchBrowser();
  try {
    const context = await browser.newContext({
      viewport: { width: 1200, height: 760 },
      deviceScaleFactor: 2,
      extraHTTPHeaders: renderHeaders(req),
    });
    const page = await context.newPage();
    const response = await page.goto(target.toString(), {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
    if (!response?.ok()) {
      throw new Error(`Print route returned ${response?.status() ?? "no response"}`);
    }
    assertNotLoginPage(page.url());
    await page.waitForSelector('[data-export-ready="true"]', { timeout: 30_000 });
    await page.waitForLoadState("networkidle", { timeout: 10_000 }).catch(() => undefined);
    const chart = page.locator('[data-chart-export-target="true"]').first();
    await chart.waitFor({ state: "visible", timeout: 30_000 });
    await page.waitForTimeout(800);
    return await chart.screenshot({
      type: "png",
      animations: "disabled",
      omitBackground: false,
    });
  } catch (error) {
    throw normalizePdfError(error, target);
  } finally {
    await browser.close();
  }
}

async function launchBrowser(): ReturnType<typeof chromium.launch> {
  const executablePath =
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH ??
    process.env.CHROMIUM_EXECUTABLE_PATH;

  try {
    return await chromium.launch({
      ...(executablePath ? { executablePath } : {}),
      args: ["--no-sandbox", "--disable-dev-shm-usage"],
    });
  } catch (error) {
    throw normalizePdfError(error);
  }
}

export function pdfExportErrorMessage(error: unknown): string {
  return exportErrorMessage(error, "PDF");
}

export function pngExportErrorMessage(error: unknown): string {
  return exportErrorMessage(error, "PNG");
}

function exportErrorMessage(error: unknown, format: "PDF" | "PNG"): string {
  const message =
    error instanceof PdfRenderError
      ? error.message
      : error instanceof Error
        ? normalizePdfError(error).message
        : "Export PDF impossible: erreur inconnue pendant la génération.";
  return message.replace(/^Export PDF impossible:/, `Export ${format} impossible:`);
}

function normalizePdfError(error: unknown, target?: URL): PdfRenderError {
  if (error instanceof PdfRenderError) return error;

  const message = error instanceof Error ? error.message : String(error);
  if (
    message.includes("Executable doesn't exist") ||
    message.includes("playwright install")
  ) {
    return new PdfRenderError(
      "Export PDF impossible: le navigateur Chromium de Playwright n'est pas installé. Exécutez `cd apps/web && npx playwright install chromium`, puis relancez le serveur web.",
      error,
    );
  }

  if (message.includes("Target page, context or browser has been closed")) {
    return new PdfRenderError(
      "Export PDF impossible: Chromium n'a pas pu démarrer dans cet environnement. Vérifiez les dépendances système du conteneur ou définissez PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH.",
      error,
    );
  }

  if (message.includes("Print route returned")) {
    return new PdfRenderError(
      `Export PDF impossible: la page d'impression a refusé le rendu${target ? ` (${target.pathname})` : ""}.`,
      error,
    );
  }

  if (message.includes("Print route redirected to login")) {
    return new PdfRenderError(
      "Export PDF impossible: la page d'impression demande une reconnexion. Rechargez la page, reconnectez-vous, puis relancez l'export.",
      error,
    );
  }

  if (message.includes("Timeout")) {
    return new PdfRenderError(
      `Export PDF impossible: la page d'impression n'a pas fini de se préparer à temps${target ? ` (${target.pathname})` : ""}.`,
      error,
    );
  }

  return new PdfRenderError(
    `Export PDF impossible: ${message || "erreur pendant la génération."}`,
    error,
  );
}

function printUrl(req: NextRequest, chartId?: DashboardChartId): URL {
  const base = pdfRenderBaseUrl(req);
  const url = new URL("/dashboard/macro-national/print", base);
  const startDate = req.nextUrl.searchParams.get("startDate");
  const endDate = req.nextUrl.searchParams.get("endDate");
  if (startDate) url.searchParams.set("startDate", startDate);
  if (endDate) url.searchParams.set("endDate", endDate);
  if (chartId) url.searchParams.set("chartId", chartId);
  return url;
}

function pdfRenderBaseUrl(req: NextRequest): string {
  if (process.env.PDF_RENDER_BASE_URL) {
    return process.env.PDF_RENDER_BASE_URL;
  }

  if (process.env.NEXTAUTH_URL) {
    return process.env.NEXTAUTH_URL;
  }

  return req.nextUrl.origin;
}

function renderHeaders(req: NextRequest): Record<string, string> {
  const headers: Record<string, string> = {};
  const cookie = req.headers.get("cookie");
  const forwardedHost = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  const forwardedProto =
    req.headers.get("x-forwarded-proto") ?? req.nextUrl.protocol.replace(":", "");

  if (cookie) headers.cookie = cookie;
  if (forwardedHost) headers["x-forwarded-host"] = forwardedHost;
  if (forwardedProto) headers["x-forwarded-proto"] = forwardedProto;
  return headers;
}

function assertNotLoginPage(url: string): void {
  try {
    const current = new URL(url);
    if (current.pathname.startsWith("/login")) {
      throw new Error("Print route redirected to login");
    }
  } catch (error) {
    if (error instanceof Error && error.message === "Print route redirected to login") {
      throw error;
    }
  }
}
