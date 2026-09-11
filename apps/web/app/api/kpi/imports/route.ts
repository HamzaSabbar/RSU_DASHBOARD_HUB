import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { canManageReports } from "@/lib/roles";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_URL_INTERNAL = process.env.API_URL_INTERNAL ?? "http://api:8000";

async function accessTokenOrResponse(
  requireManager: boolean,
): Promise<{ token: string } | NextResponse> {
  const session = (await auth()) as Record<string, unknown> | null;
  const accessToken = session?.accessToken as string | undefined;
  if (!accessToken) {
    return NextResponse.json({ detail: "unauthenticated" }, { status: 401 });
  }
  if (requireManager) {
    const role = session?.user && typeof session.user === "object"
      ? (session.user as { role?: string }).role
      : undefined;
    if (!canManageReports(role)) {
      return NextResponse.json({ detail: "forbidden" }, { status: 403 });
    }
  }
  return { token: accessToken };
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const auth_ = await accessTokenOrResponse(true);
  if (auth_ instanceof NextResponse) return auth_;

  const sourceUrl = new URL(req.url);
  const targetUrl = new URL("/api/kpi/imports", API_URL_INTERNAL);
  const mode = sourceUrl.searchParams.get("mode");
  if (mode) targetUrl.searchParams.set("mode", mode);

  const formData = await req.formData();
  const res = await fetch(targetUrl, {
    method: "POST",
    headers: { Authorization: `Bearer ${auth_.token}` },
    body: formData,
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
  });
}

export async function GET(req: NextRequest): Promise<NextResponse> {
  const auth_ = await accessTokenOrResponse(false);
  if (auth_ instanceof NextResponse) return auth_;

  const sourceUrl = new URL(req.url);
  const targetUrl = new URL("/api/kpi/imports", API_URL_INTERNAL);
  targetUrl.search = sourceUrl.search;

  const res = await fetch(targetUrl, {
    headers: { Authorization: `Bearer ${auth_.token}` },
    cache: "no-store",
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
  });
}
