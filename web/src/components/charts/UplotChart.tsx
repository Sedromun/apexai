"use client";

import uPlot from "uplot";
import { useEffect, useRef } from "react";

/** Thin React wrapper around uPlot: create on mount, resize with the container, setData on change. */
export function UplotChart({
  data,
  options,
  height = 150,
}: {
  data: (number | null)[][];
  options: Omit<uPlot.Options, "width" | "height">;
  height?: number;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<uPlot | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const width = host.clientWidth || 600;
    const chart = new uPlot(
      { ...options, width, height } as uPlot.Options,
      data as unknown as uPlot.AlignedData,
      host,
    );
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
    // Initial `data` is applied on create; later updates flow through the setData effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options, height]);

  useEffect(() => {
    chartRef.current?.setData(data as unknown as uPlot.AlignedData);
  }, [data]);

  return <div ref={hostRef} className="w-full" />;
}
