import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND, REFRESH_COOKIE } from "@/lib/server";

export async function POST() {
  const jar = await cookies();
  const refreshToken = jar.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) {
    return NextResponse.json(
      { error: { code: "no_refresh", message: "No active session" } },
      { status: 401 },
    );
  }

  const res = await fetch(`${BACKEND}/auth/refresh`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  const data = await res.json();

  if (!res.ok) {
    // Stale/invalid refresh token — clear it so the client falls back to login.
    const out = NextResponse.json(data, { status: res.status });
    out.cookies.delete(REFRESH_COOKIE);
    return out;
  }

  const tokens = data as { access_token: string; expires_in: number };
  return NextResponse.json({ access_token: tokens.access_token, expires_in: tokens.expires_in });
}
