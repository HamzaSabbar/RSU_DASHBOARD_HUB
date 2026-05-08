import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { isDashboardChartId } from "@/lib/dashboard-export";
import { pdfExportErrorMessage, renderDashboardPdf } from "@/lib/pdf-render";
import { canManageReports } from "@/lib/roles";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: { chartId: string } },
): Promise<NextResponse> {
  const session = (await auth()) as Record<string, unknown> | null;
  if (!session?.accessToken) {
    return NextResponse.json({ detail: "unauthenticated" }, { status: 401 });
  }
  const role = session?.user && typeof session.user === "object"
    ? (session.user as { role?: string }).role
    : undefined;
  if (!canManageReports(role)) {
    return NextResponse.json({ detail: "forbidden" }, { status: 403 });
  }
  if (!isDashboardChartId(params.chartId)) {
    return NextResponse.json({ detail: "unknown chart" }, { status: 404 });
  }

  try {
    const pdf = await renderDashboardPdf(req, { chartId: params.chartId });
    const filename = `rsu-dashboard-${params.chartId}.pdf`;
    return new NextResponse(new Uint8Array(pdf), {
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (error) {
    console.error(`Dashboard chart PDF export failed: ${params.chartId}`, error);
    return NextResponse.json(
      {
        detail: {
          code: "PDF_EXPORT_FAILED",
          message: pdfExportErrorMessage(error),
        },
      },
      { status: 500 },
    );
  }
}
