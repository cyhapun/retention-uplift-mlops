import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const apiUrl = process.env.API_INTERNAL_URL ?? "http://api:8000";

  try {
    const response = await fetch(`${apiUrl}/decide-action`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Decision API is unavailable." }, { status: 503 });
  }
}
