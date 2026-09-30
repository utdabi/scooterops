import { NextResponse } from "next/server"

const upstreamApiUrl = process.env.SCOOTEROPS_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"

export async function POST() {
  let upstreamResponse: Response

  try {
    upstreamResponse = await fetch(`${upstreamApiUrl}/api/analysis`, {
      method: "POST",
      cache: "no-store",
      headers: { Accept: "application/json" },
    })
  } catch (error) {
    console.error("ScooterOps analysis proxy could not reach the backend", error)
    return NextResponse.json({ detail: "The analysis service could not be reached." }, { status: 502 })
  }

  const body = await upstreamResponse.text()
  return new NextResponse(body, {
    status: upstreamResponse.status,
    headers: { "Content-Type": upstreamResponse.headers.get("content-type") ?? "application/json" },
  })
}
