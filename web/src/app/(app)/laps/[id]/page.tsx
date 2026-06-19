"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { TelemetryView } from "@/components/charts/TelemetryView";
import { CoachPanel } from "@/components/CoachPanel";
import { CornersTable } from "@/components/CornersTable";
import { TrackMap } from "@/components/TrackMap";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/cn";
import { fmtLapTime } from "@/lib/format";
import { useCompare, useLap, useLapTrace } from "@/lib/queries";
import type { LapCompare } from "@/lib/types";

function SummaryChip({
  label,
  value,
  dot,
  accent,
}: {
  label: string;
  value: string;
  dot?: string;
  accent?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-full border px-4 py-2",
        accent ? "border-primary/40 bg-primary/10" : "border-border bg-surface",
      )}
    >
      {dot && <span className="h-2 w-2 rounded-full" style={{ backgroundColor: dot }} />}
      <span className="text-xs text-muted">{label}</span>
      <span
        className={cn(
          "font-display text-base font-semibold tabular-nums",
          accent ? "text-primary" : "text-foreground",
        )}
      >
        {value}
      </span>
    </div>
  );
}

function sectors(compare: LapCompare): { label: string; delta: number }[] {
  const d = compare.delta_s;
  const n = d.length;
  if (n < 4) return [];
  const bounds = [0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1];
  return [0, 1, 2].map((i) => ({
    label: `S${i + 1}`,
    delta: Number((d[bounds[i + 1]] - d[bounds[i]]).toFixed(2)),
  }));
}

export default function LapPage() {
  const { id: lapId } = useParams<{ id: string }>();

  const { data: lap, isLoading: lapLoading, error } = useLap(lapId);
  const { data: trace, isLoading: traceLoading } = useLapTrace(lapId);
  const referenceId = lap?.reference_lap_id ?? undefined;
  const { data: referenceTrace } = useLapTrace(referenceId);
  const { data: compare } = useCompare(lapId, referenceId);

  if (lapLoading || traceLoading) return <Spinner label="Загрузка круга…" />;
  if (error || !lap || !trace)
    return <p className="text-sm text-negative">Не удалось загрузить круг.</p>;

  const summary = lap.metrics?.summary;
  const distanceKm = summary ? (summary.distance_m / 1000).toFixed(2) : null;
  const biggestLoss = compare?.corners
    .filter((c) => c.delta_s > 0)
    .sort((a, b) => b.delta_s - a.delta_s)[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/laps" className="text-sm text-muted transition hover:text-foreground">
          ← Круги
        </Link>
        <div className="mt-2 flex flex-wrap items-end gap-x-4 gap-y-1">
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            {lap.track ?? "Круг"}
          </h1>
          {!lap.valid && <Badge className="bg-surface-2 text-negative">невалидный</Badge>}
        </div>
        <p className="mt-1 font-mono text-xs uppercase tracking-widest text-muted">
          {lap.game.replace("_", " ")} · {lap.car_or_team ?? "—"}
        </p>
      </div>

      {/* Summary chips */}
      <div className="flex flex-wrap items-center gap-3">
        <SummaryChip label="Твой круг" value={fmtLapTime(lap.lap_time_ms)} dot="#f4f6fb" />
        {compare && (
          <SummaryChip label="Эталон" value={fmtLapTime(compare.b.lap_time_ms)} dot="#5a626e" />
        )}
        {compare && (
          <SummaryChip
            label="Дельта"
            value={`${compare.total_delta_s > 0 ? "+" : ""}${compare.total_delta_s.toFixed(2)}`}
            accent
          />
        )}
        <a
          href="#coach"
          className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-[#ff2d46] to-[#ff5b73] px-5 py-2 text-sm font-medium text-white shadow-[0_6px_24px_-8px_rgba(255,45,70,0.7)] transition hover:brightness-110"
        >
          🧠 Разбор AI
        </a>
      </div>

      {/* Telemetry + track map */}
      <div className="grid gap-5 md:grid-cols-3">
        <div className="md:col-span-2">
          <TelemetryView trace={trace} reference={referenceTrace} compare={compare} />
        </div>

        <div className="space-y-4">
          <Card className="p-4">
            <div className="mb-1 flex items-center justify-between">
              <CardTitle>Карта трассы</CardTitle>
              {distanceKm && (
                <span className="font-mono text-[11px] uppercase tracking-widest text-muted">
                  {distanceKm} км
                </span>
              )}
            </div>
            <TrackMap />
            {compare && (
              <div className="mt-3 grid grid-cols-3 gap-2">
                {sectors(compare).map((s) => (
                  <div key={s.label} className="rounded-xl border border-border bg-surface-2 p-2 text-center">
                    <div className="font-mono text-[11px] tracking-widest text-muted">{s.label}</div>
                    <div
                      className={cn(
                        "font-display text-sm font-semibold tabular-nums",
                        s.delta > 0 ? "text-negative" : "text-positive",
                      )}
                    >
                      {s.delta > 0 ? "+" : ""}
                      {s.delta.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {biggestLoss && (
            <Card className="border-primary/30 bg-primary/5 p-4">
              <CardTitle className="text-primary">Крупнейшая потеря</CardTitle>
              <p className="mt-1 text-sm text-foreground">
                Поворот {biggestLoss.number} — теряешь{" "}
                <span className="font-display font-semibold">{biggestLoss.delta_s.toFixed(2)} с</span>{" "}
                <span className="text-muted">(апекс {biggestLoss.self_apex_kmh} км/ч)</span>
              </p>
            </Card>
          )}

          {summary && (
            <Card className="p-4">
              <CardTitle>Сводка</CardTitle>
              <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <Stat label="Макс. скорость" value={`${summary.top_speed_kmh} км/ч`} />
                <Stat label="Полный газ" value={`${summary.full_throttle_pct}%`} />
                <Stat label="Под тормозом" value={`${summary.braking_pct}%`} />
                <Stat label="Поворотов" value={String(summary.corner_count)} />
              </dl>
            </Card>
          )}
        </div>
      </div>

      <div id="coach" className="scroll-mt-6">
        <CoachPanel lapId={lapId} />
      </div>

      {lap.metrics && lap.metrics.corners.length > 0 && (
        <div>
          <h2 className="mb-2 font-display text-lg font-semibold">По поворотам</h2>
          <CornersTable corners={lap.metrics.corners} />
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-display font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
