import { NextRequest, NextResponse } from "next/server";
import { isDashboardViewId } from "@/lib/dashboard-export";
import { pdfExportErrorMessage, renderDashboardPdf } from "@/lib/pdf-render";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest): Promise<NextResponse | Response> {
  const view = req.nextUrl.searchParams.get("view") ?? "overview";
  if (!isDashboardViewId(view)) {
    return NextResponse.json({ detail: "vue inconnue" }, { status: 400 });
  }

  try {
    const pdf = await renderDashboardPdf(req, view);
    return new Response(new Uint8Array(pdf), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="rsu-kpi-${view}.pdf"`,
      },
    });
  } catch (error) {
    return NextResponse.json({ detail: pdfExportErrorMessage(error) }, { status: 502 });
  }
}
