"use client";

import uPlot from "uplot";
import { useMemo } from "react";
import type { LapCompare } from "@/lib/types";
import { UplotChart } from "./UplotChart";

const GRID = "#272c34";
const AXIS = "#9aa3af";

/** Delta-time-by-distance: positive => current lap is slower than the reference. */
export function DeltaChart({ compare }: { compare: LapCompare }) {
  const { data, options } = useMemo(() => {
    const data: (number | null)[][] = [compare.distance_m, compare.delta_s];
    const options: Omit<uPlot.Options, "width" | "height"> = {
      scales: { x: { time: false }, y: {} },
      cursor: { sync: { key: "lap" }, points: { size: 6 }, focus: { prox: 30 } },
      legend: { show: true },
      series: [{}, { label: "Δ к эталону, с (+ медленнее)", stroke: "#e6e9ee", width: 1.5 }],
      axes: [
        { stroke: AXIS, grid: { stroke: GRID, width: 1 }, ticks: { stroke: GRID } },
        { stroke: AXIS, grid: { stroke: GRID, width: 1 }, ticks: { stroke: GRID }, size: 52 },
      ],
    };
    return { data, options };
  }, [compare]);

  return <UplotChart data={data} options={options} height={150} />;
}
