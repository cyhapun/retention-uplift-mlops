import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";

  try {
    const response = await fetch(`${opsUrl}/dashboard/drift`, { cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Drift service is unavailable." }, { status: 503 });
  }
}
