import { NextResponse } from "next/server";
import { REFRESH_COOKIE } from "@/lib/server";

export async function POST() {
  const out = NextResponse.json({ ok: true });
  out.cookies.delete(REFRESH_COOKIE);
  return out;
}
