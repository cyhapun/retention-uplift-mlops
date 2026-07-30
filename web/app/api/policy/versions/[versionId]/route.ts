import { NextRequest, NextResponse } from "next/server";

export async function DELETE(request: NextRequest, context: { params: Promise<{ versionId: string }> }) {
  const { versionId } = await context.params;
  const opsUrl = process.env.OPS_INTERNAL_URL ?? "http://ops:8001";
  const token = process.env.OPS_ADMIN_TOKEN ?? "";
  try {
    const response = await fetch(`${opsUrl}/policy/versions/${versionId}`, {
      method: "DELETE",
      headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), "content-type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
    if (response.status === 204) return new NextResponse(null, { status: 204 });
    return NextResponse.json(await response.json(), { status: response.status });
  } catch {
    return NextResponse.json({ detail: "Policy version service is unavailable." }, { status: 503 });
  }
}
