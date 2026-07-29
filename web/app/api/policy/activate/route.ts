import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";
  try {
    const response = await fetch(`${opsUrl}/policy/activate`, { method: "POST", headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), "content-type": "application/json" }, body: await request.text(), cache: "no-store" });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Policy activation service is unavailable." }, { status: 503 });
  }
}
