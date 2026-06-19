# ApexAI web cabinet (Next.js 16 · TypeScript · Tailwind v4 · uPlot)

The personal cabinet: dashboard, sessions/laps, the telemetry lap view (uPlot charts + reference
overlay + delta-time), AI coach panel, and account/subscription.

> Note: this is **Next.js 16** — `cookies()`/`params`/`searchParams` are async, Turbopack is the
> default, `next lint` is removed (`npm run lint` calls ESLint directly).

## Layout

```
src/
  app/
    (app)/            authenticated routes: dashboard, laps, laps/[id], account
    api/auth/*        BFF route handlers (login/register/refresh/logout) — manage the httpOnly cookie
    login/            login + register
    layout.tsx, providers.tsx
  components/         AppShell, SessionCard, CoachPanel, CornersTable, ui/*, charts/*
  lib/               api client, auth context, query hooks, types, formatters
```

## Auth model

Access token lives in memory; the refresh token is kept in an **httpOnly cookie** set by the Next.js
route handlers (BFF), so JS never touches it. `lib/api.ts` transparently refreshes on a 401 and
retries once. Data requests go straight to the backend with a Bearer token (CORS-allowed origin).

## Run

```bash
cp .env.example .env.local      # NEXT_PUBLIC_API_BASE / API_BASE → http://localhost:8000
npm install
npm run dev                     # http://localhost:3000
```

Log in as the seeded `demo@apexai.dev` / `demo12345`.

## Build / lint

```bash
npm run build      # type-checks (strict) + compiles
npm run lint
```

## Charts

`components/charts/UplotChart.tsx` wraps uPlot; `TelemetryView` renders synced speed / throttle+brake
/ steering / gear charts with an optional reference-lap overlay and channel toggles; `DeltaChart`
draws the delta-time-by-distance curve. Restyle freely when the visual design lands.
