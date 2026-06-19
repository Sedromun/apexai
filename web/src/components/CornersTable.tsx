"use client";

import type { Corner, TrackInfo } from "@/lib/types";

/** Approximate official corner name for a detected braking corner, by lap position. */
function officialName(apexDistM: number, track: TrackInfo | null | undefined): string | null {
  if (!track || !track.length_m || track.corners.length === 0) return null;
  const frac = Math.max(0, Math.min(1, apexDistM / track.length_m));
  const idx = Math.min(track.corners.length - 1, Math.round(frac * (track.corners.length - 1)));
  return track.corners[idx]?.name ?? null;
}

export function CornersTable({ corners, track }: { corners: Corner[]; track?: TrackInfo | null }) {
  if (corners.length === 0 && !track) return null;

  return (
    <div className="space-y-3">
      {track && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
          <span className="font-medium text-foreground">{track.name}</span>
          <span className="text-muted">{track.corner_count} поворотов</span>
          {track.record && (
            <span className="font-mono text-xs text-muted">рекорд {track.record}</span>
          )}
        </div>
      )}

      {corners.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted">
              <tr className="border-b border-border text-left">
                <th className="px-3 py-2">Поворот</th>
                <th className="px-3 py-2">Вход</th>
                <th className="px-3 py-2">Апекс</th>
                <th className="px-3 py-2">Выход</th>
                <th className="px-3 py-2">Торм.→апекс</th>
                <th className="px-3 py-2">Трейл-брейк</th>
                <th className="px-3 py-2">Коррекц.</th>
              </tr>
            </thead>
            <tbody>
              {corners.map((c) => {
                const name = officialName(c.apex_dist_m, track);
                return (
                  <tr key={c.number} className="border-b border-border/50 last:border-0">
                    <td className="px-3 py-2 font-medium">
                      Т{c.number}{" "}
                      <span className="text-muted">{c.direction === "left" ? "◄" : "►"}</span>
                      {name && <span className="ml-1.5 text-xs font-normal text-muted">{name}</span>}
                    </td>
                    <td className="px-3 py-2 font-mono">{c.entry_speed_kmh}</td>
                    <td className="px-3 py-2 font-mono">{c.apex_speed_kmh}</td>
                    <td className="px-3 py-2 font-mono">{c.exit_speed_kmh}</td>
                    <td className="px-3 py-2 font-mono">{c.brake_to_apex_m} м</td>
                    <td className="px-3 py-2 font-mono">{c.trail_brake_overlap_m} м</td>
                    <td className="px-3 py-2 font-mono">{c.steering_reversals}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {track && track.corners.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] leading-relaxed text-muted">
          {track.corners.map((tc) => (
            <span key={tc.n}>
              <span className="text-foreground/60">{tc.n}</span> {tc.name}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
