import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";

  try {
    const response = await fetch(`${opsUrl}/dashboard/overview`, { cache: "no-store" });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}
