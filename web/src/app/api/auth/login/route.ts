import { NextResponse } from "next/server";
import { BACKEND, REFRESH_COOKIE, refreshCookieOptions } from "@/lib/server";

interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export async function POST(request: Request) {
  const body = await request.json();
  const res = await fetch(`${BACKEND}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) return NextResponse.json(data, { status: res.status });

  const tokens = data as TokenPair;
  const out = NextResponse.json({ access_token: tokens.access_token, expires_in: tokens.expires_in });
  out.cookies.set(REFRESH_COOKIE, tokens.refresh_token, refreshCookieOptions);
  return out;
}
