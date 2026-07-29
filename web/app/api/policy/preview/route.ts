import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  try {
    const response = await fetch(`${opsUrl}/policy/preview`, { method: "POST", headers: { "content-type": "application/json" }, body: await request.text(), cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Policy preview service is unavailable." }, { status: 503 });
  }
}
