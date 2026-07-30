import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ simulationId: string }> },
) {
  const { simulationId } = await context.params;
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";
  try {
    const response = await fetch(`${opsUrl}/simulations/${encodeURIComponent(simulationId)}`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}

export async function POST(
  request: Request,
  context: { params: Promise<{ simulationId: string }> },
) {
  const { simulationId } = await context.params;
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";
  try {
    const response = await fetch(`${opsUrl}/simulations/${encodeURIComponent(simulationId)}/predict`, {
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
