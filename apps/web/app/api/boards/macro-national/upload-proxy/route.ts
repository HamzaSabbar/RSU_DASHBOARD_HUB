import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_URL_INTERNAL = process.env.API_URL_INTERNAL ?? "http://api:8000";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const session = (await auth()) as Record<string, unknown> | null;
  const accessToken = session?.accessToken as string | undefined;
  if (!accessToken) {
    return NextResponse.json({ detail: "unauthenticated" }, { status: 401 });
  }

  const formData = await req.formData();
  const res = await fetch(`${API_URL_INTERNAL}/api/boards/macro-national/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: formData,
  });

  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("Content-Type") ?? "application/json",
    },
  });
}
