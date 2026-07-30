import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const url = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";
  const limit = request.nextUrl.searchParams.get("limit") ?? "25";
  try {
    const response = await fetch(`${url}/simulation-predictions?limit=${encodeURIComponent(limit)}`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}
