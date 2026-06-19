"use client";

import type { TrackMapGeo } from "@/lib/types";

/** Real circuit outline (normalized SVG path from bacinger/f1-circuits, MIT). */
export function TrackMap({ map }: { map?: TrackMapGeo | null }) {
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
    </svg>
  );
}
