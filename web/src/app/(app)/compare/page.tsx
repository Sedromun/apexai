"use client";

import { useState } from "react";
import { TelemetryView } from "@/components/charts/TelemetryView";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/cn";
import { fmtLapTime } from "@/lib/format";
import { useAllLaps, useCompare, useLapTrace } from "@/lib/queries";
import type { CompareCorner, LapListItem } from "@/lib/types";

function lapLabel(lap: LapListItem): string {
  return `${lap.track ?? "—"} · ${fmtLapTime(lap.lap_time_ms)}${lap.valid ? "" : " (невал.)"}`;
}

function LapSelect({
  laps,
  value,
  exclude,
  onChange,
}: {
  laps: LapListItem[];
  value: string | undefined;
  exclude: string | undefined;
  onChange: (id: string | undefined) => void;
}) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || undefined)}
      className="w-full rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-sm text-foreground outline-none transition focus:border-primary"
    >
      <option value="">— выбери круг —</option>
      {laps
        .filter((lap) => lap.id !== exclude)
        .map((lap) => (
          <option key={lap.id} value={lap.id}>
            {lapLabel(lap)}
          </option>
        ))}
    </select>
  );
}

function SummaryChip({ label, value, dot, accent }: { label: string; value: string; dot?: string; accent?: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-full border px-4 py-2",
        accent ? "border-primary/40 bg-primary/10" : "border-border bg-surface",
      )}
    >
      {dot && <span className="h-2 w-2 rounded-full" style={{ backgroundColor: dot }} />}
      <span className="text-xs text-muted">{label}</span>
      <span className={cn("font-display text-base font-semibold tabular-nums", accent ? "text-primary" : "text-foreground")}>
        {value}
      </span>
    </div>
  );
}

function SegmentTable({ corners }: { corners: CompareCorner[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
      <table className="w-full text-sm">
        <thead className="text-xs text-muted">
          <tr className="border-b border-border text-left">
            <th className="px-3 py-2">Поворот</th>
            <th className="px-3 py-2">Апекс, м</th>
            <th className="px-3 py-2">Скорость A</th>
            <th className="px-3 py-2">Δ время, с</th>
          </tr>
        </thead>
        <tbody>
          {corners.map((c) => (
            <tr key={c.number} className="border-b border-border/50 last:border-0">
              <td className="px-3 py-2 font-medium">Т{c.number}</td>
              <td className="px-3 py-2 font-mono">{c.apex_dist_m}</td>
              <td className="px-3 py-2 font-mono">{c.self_apex_kmh} км/ч</td>
              <td
                className={cn(
                  "px-3 py-2 font-mono font-semibold",
                  c.delta_s > 0 ? "text-negative" : "text-positive",
                )}
              >
                {c.delta_s > 0 ? "+" : ""}
                {c.delta_s.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ComparePage() {
  const { data: laps, isLoading } = useAllLaps();
  const [a, setA] = useState<string | undefined>();
  const [b, setB] = useState<string | undefined>();

  // Default to the two most recent laps until the user picks (computed, no effect needed).
  const effA = a ?? laps?.[0]?.id;
  const effB = b ?? laps?.[1]?.id;

  const ready = Boolean(effA) && Boolean(effB) && effA !== effB;
  const { data: traceA } = useLapTrace(effA);
  const { data: traceB } = useLapTrace(effB);
  const { data: compare } = useCompare(ready ? effA : undefined, ready ? effB : undefined);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Сравнение кругов</h1>
        <p className="mt-1 text-sm text-muted">
          Выбери два круга — наложение каналов и дельта по дистанции.
        </p>
      </div>

      {isLoading && <Spinner label="Загрузка кругов…" />}

      {laps && laps.length < 2 && (
        <Card>
          <p className="text-sm text-muted">
            Нужно минимум два круга. Проедь ещё круг или загрузи через десктоп-клиент.
          </p>
        </Card>
      )}

      {laps && laps.length >= 2 && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1.5 flex items-center gap-2 text-xs text-muted">
                <span className="h-2 w-2 rounded-full bg-[#f4f6fb]" /> Круг A
              </div>
              <LapSelect laps={laps} value={effA} exclude={effB} onChange={setA} />
            </div>
            <div>
              <div className="mb-1.5 flex items-center gap-2 text-xs text-muted">
                <span className="h-2 w-2 rounded-full bg-[#5a626e]" /> Круг B (эталон)
              </div>
              <LapSelect laps={laps} value={effB} exclude={effA} onChange={setB} />
            </div>
          </div>

          {compare && (
            <div className="flex flex-wrap items-center gap-3">
              <SummaryChip label="Круг A" value={fmtLapTime(compare.a.lap_time_ms)} dot="#f4f6fb" />
              <SummaryChip label="Круг B" value={fmtLapTime(compare.b.lap_time_ms)} dot="#5a626e" />
              <SummaryChip
                label="Дельта"
                value={`${compare.total_delta_s > 0 ? "+" : ""}${compare.total_delta_s.toFixed(2)}`}
                accent
              />
            </div>
          )}

          {!ready ? (
            <Card>
              <p className="text-sm text-muted">Выбери два разных круга для сравнения.</p>
            </Card>
          ) : traceA && traceB ? (
            <>
              <TelemetryView trace={traceA} reference={traceB} compare={compare} />
              {compare && compare.corners.length > 0 && (
                <div>
                  <h2 className="mb-2 font-display text-lg font-semibold">Дельта по поворотам</h2>
                  <SegmentTable corners={compare.corners} />
                </div>
              )}
            </>
          ) : (
            <Spinner label="Загрузка телеметрии…" />
          )}
        </>
      )}
    </div>
  );
}
