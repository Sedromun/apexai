"use client";

import Link from "next/link";
import { fmtDateTime, fmtLapTime } from "@/lib/format";
import { useSessionLaps } from "@/lib/queries";
import type { SessionSummary } from "@/lib/types";
import { Badge } from "./ui/Badge";
import { Spinner } from "./ui/Spinner";

export function SessionCard({ session }: { session: SessionSummary }) {
  const { data: laps, isLoading } = useSessionLaps(session.id);

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
        <div className="font-medium">{session.track ?? "Без трассы"}</div>
        <span className="text-sm text-muted">{session.car_or_team ?? "—"}</span>
        <Badge className="bg-surface-2 uppercase text-muted">{session.game}</Badge>
        <div className="ml-auto text-sm text-muted">{fmtDateTime(session.started_at)}</div>
      </div>

      <div className="px-2 py-1">
        {isLoading && (
          <div className="px-2 py-3">
            <Spinner label="Круги…" />
          </div>
        )}
        {laps && laps.length === 0 && (
          <div className="px-2 py-3 text-sm text-muted">Нет кругов</div>
        )}
        {laps?.map((lap) => {
          const isBest =
            session.best_lap_time_ms !== null &&
            lap.valid &&
            lap.lap_time_ms === session.best_lap_time_ms;
          return (
            <Link
              key={lap.id}
              href={`/laps/${lap.id}`}
              className="flex items-center gap-3 rounded-md px-2 py-2 text-sm transition hover:bg-surface-2"
            >
              <span className="font-mono">{fmtLapTime(lap.lap_time_ms)}</span>
              {isBest && <Badge className="bg-primary/15 text-primary">лучший</Badge>}
              {!lap.valid && <Badge className="bg-surface-2 text-negative">невалидный</Badge>}
              <span className="ml-auto text-muted">{fmtDateTime(lap.recorded_at)}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
