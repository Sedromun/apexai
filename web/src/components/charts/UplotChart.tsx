"use client";

import uPlot from "uplot";
import { useEffect, useRef } from "react";

/**
 * Thin React wrapper around uPlot: create on mount, resize with the container, setData on change.
 * Adds a hover callback (reports the x value under the cursor) and external x-range control so
 * several charts can share one zoom window (drag to zoom, double-click to reset).
 */
export function UplotChart({
  data,
  options,
  height = 150,
  onHover,
  onZoom,
  xRange,
}: {
  data: (number | null)[][];
  options: Omit<uPlot.Options, "width" | "height">;
  height?: number;
  onHover?: (x: number | null) => void;
  onZoom?: (range: [number, number] | null) => void;
  xRange?: [number, number] | null;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);
  const onHoverRef = useRef(onHover);
  const onZoomRef = useRef(onZoom);
  const applyingRef = useRef(false);

  useEffect(() => {
    onHoverRef.current = onHover;
    onZoomRef.current = onZoom;
  });

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const width = host.clientWidth || 600;

    const merged = { ...options, width, height } as uPlot.Options;
    merged.hooks = {
      ...(options.hooks || {}),
      setCursor: [
        ...(options.hooks?.setCursor ?? []),
        (u: uPlot) => {
          const i = u.cursor.idx;
          onHoverRef.current?.(i == null || i < 0 ? null : (u.data[0][i] as number));
        },
      ],
      setScale: [
        ...(options.hooks?.setScale ?? []),
        (u: uPlot, key: string) => {
          if (key !== "x" || applyingRef.current) return;
          const s = u.scales.x;
          const xs = u.data[0];
          if (s.min == null || s.max == null || !xs.length) return;
          const isFull = s.min <= (xs[0] as number) && s.max >= (xs[xs.length - 1] as number);
          onZoomRef.current?.(isFull ? null : [s.min, s.max]);
        },
      ],
    };

    const chart = new uPlot(merged, data as unknown as uPlot.AlignedData, host);
    chartRef.current = chart;

    // --- mouse-wheel zoom (around the cursor) + drag-to-pan ---------------------
    // setScale() fires the setScale hook above, which reports the new window up to
    // the parent and syncs every sibling chart through the shared `xRange`.
    const over = chart.over;
    const fullMin = () => chart.data[0][0] as number;
    const fullMax = () => chart.data[0][chart.data[0].length - 1] as number;
    const MIN_SPAN_FRAC = 0.015; // don't let the window shrink below ~1.5% of the lap

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const sx = chart.scales.x;
      if (sx.min == null || sx.max == null) return;
      const rect = over.getBoundingClientRect();
      if (!rect.width) return;
      const pivot = chart.posToVal(e.clientX - rect.left, "x");
      const factor = e.deltaY < 0 ? 0.82 : 1 / 0.82; // wheel up = zoom in
      const fMin = fullMin();
      const fMax = fullMax();
      let lo = pivot - (pivot - sx.min) * factor;
      let hi = pivot + (sx.max - pivot) * factor;
      lo = Math.max(fMin, lo);
      hi = Math.min(fMax, hi);
      if (hi - lo < (fMax - fMin) * MIN_SPAN_FRAC) return;
      if (lo >= hi) return;
      chart.setScale("x", { min: lo, max: hi });
    };

    let panning = false;
    let panStartX = 0;
    let panMin = 0;
    let panMax = 0;
    const onDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      const sx = chart.scales.x;
      if (sx.min == null || sx.max == null) return;
      panning = true;
      panStartX = e.clientX;
      panMin = sx.min;
      panMax = sx.max;
      over.style.cursor = "grabbing";
    };
    const onMove = (e: MouseEvent) => {
      if (!panning) return;
      const rect = over.getBoundingClientRect();
      if (!rect.width) return;
      const span = panMax - panMin;
      const dx = ((e.clientX - panStartX) / rect.width) * span;
      const fMin = fullMin();
      const fMax = fullMax();
      let lo = panMin - dx;
      let hi = panMax - dx;
      if (lo < fMin) [lo, hi] = [fMin, fMin + span];
      if (hi > fMax) [lo, hi] = [fMax - span, fMax];
      chart.setScale("x", { min: lo, max: hi });
    };
    const onUp = () => {
      if (!panning) return;
      panning = false;
      over.style.cursor = "";
    };
    const onDblClick = () => {
      onZoomRef.current?.(null);
      chart.setScale("x", { min: fullMin(), max: fullMax() });
    };

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
  }, [options, height]);

  useEffect(() => {
    chartRef.current?.setData(data as unknown as uPlot.AlignedData);
  }, [data]);

  // Apply an externally controlled x window (shared zoom across charts).
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    applyingRef.current = true;
    if (xRange) {
      chart.setScale("x", { min: xRange[0], max: xRange[1] });
    } else {
      const xs = chart.data[0];
      if (xs && xs.length) chart.setScale("x", { min: xs[0] as number, max: xs[xs.length - 1] as number });
    }
    applyingRef.current = false;
  }, [xRange]);

  return <div ref={hostRef} className="w-full" />;
}
