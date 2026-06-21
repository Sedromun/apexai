"use client";

import { useEffect, useRef, useState } from "react";
import type { TrackMapGeo } from "@/lib/types";

/**
 * Map a lap-distance fraction onto an outline-arc-length fraction through the
 * per-track warp control points, so the marker sits on the right corner (the
 * outline's length doesn't accumulate at the lap-distance rate). Identity when
 * no warp is available.
 */
function warpFraction(f: number, cps?: [number, number][] | null): number {
  const x = Math.max(0, Math.min(1, f));
  if (!cps || cps.length < 2) return x;
  for (let i = 0; i < cps.length - 1; i++) {
    const [x0, y0] = cps[i];
    const [x1, y1] = cps[i + 1];
    if (x <= x1) return x1 > x0 ? y0 + ((x - x0) / (x1 - x0)) * (y1 - y0) : y0;
  }
  return cps[cps.length - 1][1];
}

/** Real circuit outline (normalized SVG path from bacinger/f1-circuits, MIT). */
export function TrackMap({ map, markerFrac }: { map?: TrackMapGeo | null; markerFrac?: number | null }) {
  const pathRef = useRef<SVGPathElement>(null);
  const [marker, setMarker] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    const path = pathRef.current;
    if (!path || markerFrac == null || Number.isNaN(markerFrac)) {
      setMarker(null);
      return;
    }
    const len = path.getTotalLength();
    const p = path.getPointAtLength(len * warpFraction(markerFrac, map?.align_warp));
    setMarker({ x: p.x, y: p.y });
  }, [markerFrac, map]);

  if (!map) {
    return (
      <div className="flex h-44 items-center justify-center rounded-xl border border-border bg-surface-2 px-4 text-center text-xs text-muted">
        Карта для этой трассы пока недоступна
      </div>
    );
  }

  return (
    <svg viewBox={map.view_box} className="w-full" style={{ maxHeight: 300 }} role="img" aria-label="Карта трассы">
      <defs>
        <filter id="trackglow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="7" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      {/* tarmac underlay */}
      <path d={map.path} fill="none" stroke="#2a3038" strokeWidth="16" strokeLinejoin="round" strokeLinecap="round" />
      {/* racing line */}
      <path
        ref={pathRef}
        d={map.path}
        fill="none"
        stroke="#ff2d46"
        strokeWidth="6"
        strokeLinejoin="round"
        strokeLinecap="round"
        filter="url(#trackglow)"
      />
      {/* start / finish */}
      <circle cx={map.start.x} cy={map.start.y} r="13" fill="#3ddc84" stroke="#0a0c0f" strokeWidth="3" />
      {/* position under the chart cursor */}
      {marker && (
        <g>
          <circle cx={marker.x} cy={marker.y} r="24" fill="#22d3ee" opacity="0.25" />
          <circle cx={marker.x} cy={marker.y} r="11" fill="#22d3ee" stroke="#0a0c0f" strokeWidth="3" />
        </g>
      )}
    </svg>
  );
}
