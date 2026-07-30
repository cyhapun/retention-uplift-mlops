import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function opsConfig() {
  return {
    url: process.env.OPS_INTERNAL_URL ?? "http://ops:8001",
    token: process.env.OPS_ADMIN_TOKEN ?? "",
  };
}

export async function GET(request: NextRequest) {
  const { url, token } = opsConfig();
  const limit = request.nextUrl.searchParams.get("limit") ?? "25";
  try {
    const response = await fetch(`${url}/simulations?limit=${encodeURIComponent(limit)}`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}

export async function POST(request: NextRequest) {
  const { url, token } = opsConfig();
  try {
    const response = await fetch(`${url}/simulations`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(token ? { authorization: `Bearer ${token}` } : {}),
      },
      body: await request.text(),
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}
