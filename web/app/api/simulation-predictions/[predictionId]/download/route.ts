import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: Request,
  context: { params: Promise<{ predictionId: string }> },
) {
  const { predictionId } = await context.params;
  const format = new URL(request.url).searchParams.get("format") ?? "parquet";
  const url = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";
  try {
    const response = await fetch(
      `${url}/simulation-predictions/${encodeURIComponent(predictionId)}/download?format=${encodeURIComponent(format)}`,
      { headers: token ? { authorization: `Bearer ${token}` } : {}, cache: "no-store" },
    );
    if (!response.ok) return NextResponse.json(await response.json(), { status: response.status });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/octet-stream",
        "content-disposition": response.headers.get("content-disposition") ?? "attachment",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Operations service is unavailable." }, { status: 503 });
  }
}
