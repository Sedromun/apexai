// Server-only constants for the BFF auth route handlers.
export const BACKEND =
  process.env.API_BASE ?? process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export const REFRESH_COOKIE = "apex_refresh";
export const REFRESH_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

export const refreshCookieOptions = {
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax" as const,
  path: "/",
  maxAge: REFRESH_MAX_AGE,
};
