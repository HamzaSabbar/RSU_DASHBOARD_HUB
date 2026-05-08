import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { canManageReports } from "@/lib/roles";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_URL_INTERNAL = process.env.API_URL_INTERNAL ?? "http://api:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: { jobId: string } },
): Promise<NextResponse> {
  const session = (await auth()) as Record<string, unknown> | null;
  const accessToken = session?.accessToken as string | undefined;
  if (!accessToken) {
    return NextResponse.json({ detail: "unauthenticated" }, { status: 401 });
  }
  const role = session?.user && typeof session.user === "object"
    ? (session.user as { role?: string }).role
    : undefined;
  if (!canManageReports(role)) {
    return NextResponse.json({ detail: "forbidden" }, { status: 403 });
  }

  const res = await fetch(
    `${API_URL_INTERNAL}/api/reports/jobs/${encodeURIComponent(params.jobId)}/dashboard`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: "no-store",
    },
  );

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("Content-Type") ?? "application/json",
    },
  });
}
