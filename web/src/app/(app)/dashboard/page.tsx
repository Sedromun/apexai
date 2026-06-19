"use client";

import Link from "next/link";
import { SessionCard } from "@/components/SessionCard";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";
import { fmtLapTime } from "@/lib/format";
import { useSessions } from "@/lib/queries";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 font-display text-2xl font-semibold tabular-nums">{value}</div>
    </Card>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: sessions, isLoading } = useSessions();

  const bestOverall =
    sessions?.reduce<number | null>((best, s) => {
      if (s.best_lap_time_ms === null) return best;
      return best === null ? s.best_lap_time_ms : Math.min(best, s.best_lap_time_ms);
    }, null) ?? null;
  const totalLaps = sessions?.reduce((n, s) => n + s.lap_count, 0) ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">Привет, гонщик</h1>
        <p className="text-sm text-muted">
          {user?.email} · тариф {user?.plan?.toUpperCase()}
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Сессий" value={String(sessions?.length ?? 0)} />
        <Stat label="Кругов всего" value={String(totalLaps)} />
        <Stat label="Лучший круг" value={fmtLapTime(bestOverall)} />
      </div>

      {user && (
        <Card>
          <CardTitle>Лимиты тарифа</CardTitle>
          <p className="mt-2 text-sm text-muted">
            Кругов за месяц: {user.usage.laps_this_month}
            {user.plan !== "pro" && ` / ${user.limits.free_monthly_lap_limit}`} · AI-разборов:{" "}
            {user.usage.ai_reports_used}
            {user.plan !== "pro" && ` / ${user.limits.free_ai_trial} (проба)`}
          </p>
          {user.plan !== "pro" && (
            <Link href="/account" className="mt-2 inline-block text-sm text-primary hover:underline">
              Перейти на Pro →
            </Link>
          )}
        </Card>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold text-muted">Последние сессии</h2>
        {isLoading && <Spinner label="Загрузка…" />}
        {sessions && sessions.length === 0 && (
          <Card>
            <p className="text-sm text-muted">
              Пока нет заездов. Установи десктоп-клиент, включи UDP-телеметрию в F1 и проедь
              круг — он появится здесь.
            </p>
          </Card>
        )}
        <div className="space-y-3">
          {sessions?.slice(0, 3).map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      </div>
    </div>
  );
}
