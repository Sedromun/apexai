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

    const ro = new ResizeObserver(() => {
      chart.setSize({ width: host.clientWidth || width, height });
    });
    ro.observe(host);

    return () => {
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
