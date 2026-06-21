"use client";

import uPlot from "uplot";
import { useEffect, useRef } from "react";

/** New x-window when zooming around `pivot` by `factor` (<1 = zoom in), clamped to
 * [fMin,fMax]. Returns null if it would shrink below `minFrac` of the full span. */
export function zoomWindow(
  min: number,
  max: number,
  pivot: number,
  factor: number,
  fMin: number,
  fMax: number,
  minFrac = 0.015,
): [number, number] | null {
  let lo = pivot - (pivot - min) * factor;
  let hi = pivot + (max - pivot) * factor;
  lo = Math.max(fMin, lo);
  hi = Math.min(fMax, hi);
  if (hi - lo < (fMax - fMin) * minFrac || lo >= hi) return null;
  return [lo, hi];
}

/** New x-window when panning the captured [min,max] window by `dxFrac` of its span,
 * clamped to [fMin,fMax] (keeps the span fixed at the edges). */
export function panWindow(
  min: number,
  max: number,
  dxFrac: number,
  fMin: number,
  fMax: number,
): [number, number] {
  const span = max - min;
  const dx = dxFrac * span;
  let lo = min - dx;
  let hi = max - dx;
  if (lo < fMin) [lo, hi] = [fMin, fMin + span];
  if (hi > fMax) [lo, hi] = [fMax - span, fMax];
  return [lo, hi];
}

/** Index of the value in the ascending array `xs` nearest to `x`. */
export function nearestIdx(xs: ArrayLike<number>, x: number): number {
  const n = xs.length;
  if (n === 0) return 0;
  if (x <= xs[0]) return 0;
  if (x >= xs[n - 1]) return n - 1;
  let lo = 0;
  let hi = n - 1;
  while (lo <= hi) {
    const m = (lo + hi) >> 1;
    if ((xs[m] as number) < x) lo = m + 1;
    else hi = m - 1;
  }
  return Math.abs((xs[lo] as number) - x) < Math.abs((xs[lo - 1] as number) - x) ? lo : lo - 1;
}

function fmtVal(v: number, decimals: number): string {
  return decimals > 0 ? v.toFixed(decimals) : Math.round(v).toString();
}

/**
 * Thin React wrapper around uPlot. The cursor reports the x under the *vertical
 * crosshair* (not the nearest data point) so the track-map marker follows continuously
 * anywhere in the plot, and a small tooltip shows the channel value(s) at that line.
 * Mouse-wheel zooms around the cursor, drag pans, double-click resets — interactions
 * report the new window via `onZoom`, and the `xRange` effect is the single applier.
 */
export function UplotChart({
  data,
  options,
  height = 150,
  onHover,
  onZoom,
  xRange,
  unit = "",
  decimals = 0,
}: {
  data: (number | null)[][];
  options: Omit<uPlot.Options, "width" | "height">;
  height?: number;
  onHover?: (x: number | null) => void;
  onZoom?: (range: [number, number] | null) => void;
  xRange?: [number, number] | null;
  unit?: string;
  decimals?: number;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);
  const onHoverRef = useRef(onHover);
  const onZoomRef = useRef(onZoom);
  const rangeRef = useRef<[number, number] | null>(null);

  useEffect(() => {
    onHoverRef.current = onHover;
    onZoomRef.current = onZoom;
  });

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const width = host.clientWidth || 600;

    // Value readout that rides the crosshair (built imperatively; uPlot is imperative).
    const tip = document.createElement("div");
    tip.style.cssText =
      "position:absolute;top:4px;z-index:10;display:none;transform:translateX(-50%);" +
      "pointer-events:none;white-space:nowrap;line-height:1.35;";
    tip.className =
      "rounded-md border border-border bg-surface-2/95 px-2 py-1 text-[11px] font-mono shadow-lg backdrop-blur-sm";

    const merged = { ...options, width, height } as uPlot.Options;
    merged.hooks = {
      ...(options.hooks || {}),
      setCursor: [
        ...(options.hooks?.setCursor ?? []),
        (u: uPlot) => {
          const left = u.cursor.left ?? -1;
          if (left == null || left < 0) {
            onHoverRef.current?.(null);
            tip.style.display = "none";
            return;
          }
          const xv = u.posToVal(left, "x");
          onHoverRef.current?.(Number.isFinite(xv) ? xv : null);

          const xs = u.data[0] as unknown as number[];
          const idx = nearestIdx(xs, xv);
          const lines = [`<span style="opacity:.55">${Math.round(xv)} м</span>`];
          for (let s = 1; s < u.series.length; s++) {
            const v = u.data[s]?.[idx];
            if (v == null || Number.isNaN(v)) continue;
            const st = u.series[s].stroke;
            const col = typeof st === "string" ? st : "#f4f6fb";
            lines.push(
              `<span style="color:${col}">●</span> ${fmtVal(v as number, decimals)}${unit ? ` ${unit}` : ""}`,
            );
          }
          tip.innerHTML = lines.join("<br>");
          const w = u.over.clientWidth || width;
          tip.style.left = `${Math.max(30, Math.min(w - 30, left))}px`;
          tip.style.display = "block";
        },
      ],
    };

    const chart = new uPlot(merged, data as unknown as uPlot.AlignedData, host);
    chartRef.current = chart;
    chart.over.appendChild(tip);

    const over = chart.over;
    const fullMin = () => chart.data[0][0] as number;
    const fullMax = () => chart.data[0][chart.data[0].length - 1] as number;
    const curWindow = (): [number, number] => rangeRef.current ?? [fullMin(), fullMax()];
    const report = (r: [number, number] | null) => {
      rangeRef.current = r;
      onZoomRef.current?.(r);
    };
    const asReport = (lo: number, hi: number): [number, number] | null =>
      lo <= fullMin() && hi >= fullMax() ? null : [lo, hi];

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = over.getBoundingClientRect();
      if (!rect.width) return;
      const [min, max] = curWindow();
      const pivot = min + ((e.clientX - rect.left) / rect.width) * (max - min);
      const intensity = Math.min(0.3, Math.abs(e.deltaY) / 500) || 0.18;
      const factor = e.deltaY < 0 ? 1 - intensity : 1 / (1 - intensity);
      const win = zoomWindow(min, max, pivot, factor, fullMin(), fullMax());
      if (win) report(asReport(win[0], win[1]));
    };

    let panning = false;
    let panStartX = 0;
    let panMin = 0;
    let panMax = 0;
    const onDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      [panMin, panMax] = curWindow();
      panning = true;
      panStartX = e.clientX;
      over.style.cursor = "grabbing";
      e.preventDefault();
    };
    const onMove = (e: MouseEvent) => {
      if (!panning) return;
      const rect = over.getBoundingClientRect();
      if (!rect.width) return;
      const [lo, hi] = panWindow(panMin, panMax, (e.clientX - panStartX) / rect.width, fullMin(), fullMax());
      report(asReport(lo, hi));
    };
    const onUp = () => {
      if (!panning) return;
      panning = false;
      over.style.cursor = "";
    };
    const onDblClick = () => report(null);

    over.addEventListener("wheel", onWheel, { passive: false });
    over.addEventListener("mousedown", onDown);
    over.addEventListener("dblclick", onDblClick);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);

    const ro = new ResizeObserver(() => {
      chart.setSize({ width: host.clientWidth || width, height });
    });
    ro.observe(host);

    return () => {
      over.removeEventListener("wheel", onWheel);
      over.removeEventListener("mousedown", onDown);
      over.removeEventListener("dblclick", onDblClick);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      ro.disconnect();
      chart.destroy();
      chartRef.current = null;
    };
    // Initial `data` is applied on create; later updates flow through the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options, height, unit, decimals]);

  useEffect(() => {
    chartRef.current?.setData(data as unknown as uPlot.AlignedData);
  }, [data]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    rangeRef.current = xRange ?? null;
    if (xRange) {
      chart.setScale("x", { min: xRange[0], max: xRange[1] });
    } else {
      const xs = chart.data[0];
      if (xs && xs.length)
        chart.setScale("x", { min: xs[0] as number, max: xs[xs.length - 1] as number });
    }
  }, [xRange]);

  return <div ref={hostRef} className="relative w-full" />;
}
