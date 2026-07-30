import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: { params: Promise<{ predictionId: string }> },
) {
  const { predictionId } = await context.params;
  const url = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";
  try {
    const response = await fetch(`${url}/simulation-predictions/${encodeURIComponent(predictionId)}`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: "no-store",
    });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}
