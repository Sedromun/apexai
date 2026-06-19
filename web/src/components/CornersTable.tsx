"use client";

import type { Corner } from "@/lib/types";

export function CornersTable({ corners }: { corners: Corner[] }) {
  if (corners.length === 0) return null;

  return (
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
          {corners.map((c) => (
            <tr key={c.number} className="border-b border-border/50 last:border-0">
              <td className="px-3 py-2 font-medium">
                Т{c.number} <span className="text-muted">{c.direction === "left" ? "◄" : "►"}</span>
              </td>
              <td className="px-3 py-2 font-mono">{c.entry_speed_kmh}</td>
              <td className="px-3 py-2 font-mono">{c.apex_speed_kmh}</td>
              <td className="px-3 py-2 font-mono">{c.exit_speed_kmh}</td>
              <td className="px-3 py-2 font-mono">{c.brake_to_apex_m} м</td>
              <td className="px-3 py-2 font-mono">{c.trail_brake_overlap_m} м</td>
              <td className="px-3 py-2 font-mono">{c.steering_reversals}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
