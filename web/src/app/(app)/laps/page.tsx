"use client";

import { SessionCard } from "@/components/SessionCard";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useSessions } from "@/lib/queries";

export default function LapsPage() {
  const { data: sessions, isLoading, error } = useSessions();

  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl font-semibold tracking-tight">Сессии и круги</h1>

      {isLoading && <Spinner label="Загрузка сессий…" />}
      {error && <p className="text-sm text-negative">Не удалось загрузить сессии.</p>}

      {sessions && sessions.length === 0 && (
        <Card>
          <p className="text-sm text-muted">
            Пока нет заездов. Установи десктоп-клиент, включи в F1 UDP-телеметрию и проедь
            круг — он появится здесь.
          </p>
        </Card>
      )}

      <div className="space-y-3">
        {sessions?.map((session) => (
          <SessionCard key={session.id} session={session} />
        ))}
      </div>
    </div>
  );
}
