import { NextResponse } from "next/server";

export async function POST(
  _request: Request,
  context: { params: Promise<{ operation: string }> },
) {
  const { operation } = await context.params;
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";

  try {
    const response = await fetch(`${opsUrl}/operations/${operation}`, {
      method: "POST",
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}
