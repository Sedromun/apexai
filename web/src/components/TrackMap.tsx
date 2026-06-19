"use client";

import { useEffect, useRef, useState } from "react";

// A stylized closed racing line (original, not a real circuit). When the trace carries world
// position channels (real F1 data), this can be replaced with the actual path; for now it is a
// representative loop with start (green) and current-position (white) markers.
const LOOP =
  "M44 128 C 30 78, 86 44, 138 54 C 188 64, 196 36, 240 54 C 286 72, 292 120, 256 150 " +
  "C 214 186, 150 196, 116 172 C 84 150, 58 168, 44 128 Z";

export function TrackMap({ progress = 0.58 }: { progress?: number }) {
  const pathRef = useRef<SVGPathElement>(null);
  const [points, setPoints] = useState<{ start: DOMPoint; car: DOMPoint } | null>(null);

  useEffect(() => {
    const path = pathRef.current;
    if (!path) return;
    const length = path.getTotalLength();
    setPoints({ start: path.getPointAtLength(0), car: path.getPointAtLength(length * progress) });
  }, [progress]);

  return (
    <svg viewBox="0 0 320 220" className="w-full">
      <defs>
        <filter id="trackglow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        ref={pathRef}
        d={LOOP}
        fill="none"
        stroke="#ff2d46"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#trackglow)"
      />
      {points && (
        <>
          <circle cx={points.start.x} cy={points.start.y} r="5" fill="#3ddc84" />
          <circle cx={points.car.x} cy={points.car.y} r="5.5" fill="#fff" />
        </>
      )}
    </svg>
  );
}
