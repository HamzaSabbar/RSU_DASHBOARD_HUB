import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_URL_INTERNAL = process.env.API_URL_INTERNAL ?? "http://api:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ code: string }> },
): Promise<NextResponse> {
  const session = (await auth()) as Record<string, unknown> | null;
  const accessToken = session?.accessToken as string | undefined;
  if (!accessToken) {
    return NextResponse.json({ detail: "unauthenticated" }, { status: 401 });
  }

  const { code } = await params;
  const sourceUrl = new URL(req.url);
  const targetUrl = new URL(`/api/kpi/${encodeURIComponent(code)}`, API_URL_INTERNAL);
  targetUrl.search = sourceUrl.search;

  const res = await fetch(targetUrl, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
  });
}
