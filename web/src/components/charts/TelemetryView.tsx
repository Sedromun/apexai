"use client";

import uPlot from "uplot";
import { useMemo, useState } from "react";
import { Chip } from "@/components/ui/Chip";
import { resampleByDistance } from "@/lib/resample";
import type { LapCompare, LapTrace } from "@/lib/types";
import { UplotChart } from "./UplotChart";

const C = {
  speed: "#f4f6fb",
  throttle: "#3ddc84",
  brake: "#ff2d46",
  steer: "#8b7bff",
  gear: "#f5a524",
  delta: "#ff2d46",
  ghost: "#5a626e",
};
const GRID = "#1b212a";
const AXIS = "#5d6470";

type ChannelKey = "speed" | "throttle" | "brake" | "steer" | "gear" | "delta";

interface ChannelMeta {
  key: ChannelKey;
  title: string;
  unit?: string;
  color: string;
  channel?: keyof LapTrace["channels"] | string;
  fill?: string;
  scalePct?: boolean;
  yRange?: [number, number];
  stepped?: boolean;
  height: number;
}

const CHANNELS: ChannelMeta[] = [
  { key: "speed", title: "Скорость", unit: "КМ/Ч", color: C.speed, channel: "speed_kmh", fill: "rgba(244,246,251,0.06)", height: 168 },
  { key: "throttle", title: "Газ", unit: "%", color: C.throttle, channel: "throttle", fill: "rgba(61,220,132,0.10)", scalePct: true, yRange: [0, 100], height: 118 },
  { key: "brake", title: "Тормоз", unit: "%", color: C.brake, channel: "brake", fill: "rgba(255,45,70,0.10)", scalePct: true, yRange: [0, 100], height: 118 },
  { key: "steer", title: "Руль", color: C.steer, channel: "steer", yRange: [-1, 1], height: 108 },
  { key: "gear", title: "Передача", color: C.gear, channel: "gear", yRange: [0, 9], stepped: true, height: 100 },
  { key: "delta", title: "Дельта", unit: "С", color: C.delta, fill: "rgba(255,45,70,0.08)", height: 118 },
];

function options(series: uPlot.Series[], yRange?: [number, number]): Omit<uPlot.Options, "width" | "height"> {
  return {
    scales: { x: { time: false }, y: yRange ? { range: yRange } : {} },
    cursor: { sync: { key: "lap" }, points: { size: 5 }, focus: { prox: 24 } },
    legend: { show: false },
    series,
    axes: [
      { stroke: AXIS, grid: { stroke: GRID, width: 1 }, ticks: { stroke: GRID }, font: "10px monospace" },
      { stroke: AXIS, grid: { stroke: GRID, width: 1 }, ticks: { stroke: GRID }, size: 44, font: "10px monospace" },
    ],
  };
}

export function TelemetryView({
  trace,
  reference,
  compare,
}: {
  trace: LapTrace;
  reference?: LapTrace | null;
  compare?: LapCompare | null;
}) {
  const [hidden, setHidden] = useState<Set<ChannelKey>>(new Set());
  const [showRef, setShowRef] = useState(true);

  const charts = useMemo(() => {
    const x = trace.channels.lap_dist_m;
    const stepped = uPlot.paths.stepped;
    const built: Record<string, { data: (number | null)[][]; options: Omit<uPlot.Options, "width" | "height"> }> = {};

    for (const meta of CHANNELS) {
      if (meta.key === "delta") {
        if (!compare) continue;
        built.delta = {
          data: [compare.distance_m, compare.delta_s],
          options: options([{}, { stroke: meta.color, width: 1.6, fill: meta.fill }]),
        };
        continue;
      }

      const raw = trace.channels[meta.channel as string];
      const values = meta.scalePct ? raw.map((v) => v * 100) : raw;
      const data: (number | null)[][] = [x, values];
      const series: uPlot.Series[] = [
        {},
        {
          stroke: meta.color,
          width: 1.6,
          fill: meta.fill,
          paths: meta.stepped && stepped ? stepped({ align: 1 }) : undefined,
        },
      ];

      if (showRef && reference) {
        const refRaw = reference.channels[meta.channel as string];
        const resampled = resampleByDistance(reference.channels.lap_dist_m, refRaw, x);
        data.push(meta.scalePct ? resampled.map((v) => (v === null ? null : v * 100)) : resampled);
        series.push({ stroke: C.ghost, width: 1.2, dash: [5, 4] });
      }

      built[meta.key] = { data, options: options(series, meta.yRange) };
    }
    return built;
  }, [trace, reference, compare, showRef]);

  const visible = CHANNELS.filter((m) => charts[m.key] && !hidden.has(m.key));

  const toggle = (key: ChannelKey) =>
    setHidden((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        {CHANNELS.filter((m) => charts[m.key]).map((m) => (
          <Chip key={m.key} color={m.color} active={!hidden.has(m.key)} onClick={() => toggle(m.key)}>
            {m.title}
          </Chip>
        ))}
        {reference && (
          <Chip className="ml-auto" active={showRef} onClick={() => setShowRef((v) => !v)}>
            Наложить эталон
          </Chip>
        )}
      </div>

      {visible.map((m) => (
        <div key={m.key} className="rounded-2xl border border-border bg-surface p-4">
          <div className="mb-2 flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: m.color }} />
            <span className="text-sm font-medium text-foreground">{m.title}</span>
            {m.unit && (
              <span className="ml-auto font-mono text-[11px] uppercase tracking-widest text-muted">
                {m.unit}
              </span>
            )}
          </div>
          <UplotChart data={charts[m.key].data} options={charts[m.key].options} height={m.height} />
        </div>
      ))}
    </div>
  );
}
