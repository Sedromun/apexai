"use client";

import Link from "next/link";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAnalyzeLap, useCoachReport } from "@/lib/queries";
import { Button } from "./ui/Button";
import { Card, CardTitle } from "./ui/Card";
import { Spinner } from "./ui/Spinner";

export function CoachPanel({ lapId }: { lapId: string }) {
  const { user, refreshUser } = useAuth();
  const { data: report, isLoading } = useCoachReport(lapId);
  const analyze = useAnalyzeLap();

  const onAnalyze = async () => {
    try {
      await analyze.mutateAsync(lapId);
      await refreshUser(); // reflect the spent AI trial in usage counters
    } catch {
      /* error surfaced from analyze.error below */
    }
  };

  if (isLoading) {
    return (
      <Card>
        <Spinner label="Проверяем разбор…" />
      </Card>
    );
  }

  if (report) {
    const s = report.summary;
    return (
      <Card className="space-y-4">
        <div className="flex items-center gap-2">
          <CardTitle>AI-разбор тренера</CardTitle>
          <span className="ml-auto text-xs text-muted">{report.model}</span>
        </div>
        <p className="text-sm">{s.summary_text}</p>

        {s.top_mistakes.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-semibold text-muted">Три главные ошибки</div>
            <ol className="space-y-2">
              {s.top_mistakes.map((m, i) => (
                <li key={i} className="rounded-md border border-border bg-surface-2 p-3 text-sm">
                  <div className="font-medium">
                    {m.title}
                    {m.time_loss_s != null && (
                      <span className="ml-2 text-negative">≈ {m.time_loss_s.toFixed(2)} с</span>
                    )}
                  </div>
                  <div className="mt-1 text-muted">{m.detail}</div>
                </li>
              ))}
            </ol>
          </div>
        )}

        {s.training_plan.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-semibold text-muted">План на следующую сессию</div>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
              {s.training_plan.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </div>
        )}
      </Card>
    );
  }

  const error = analyze.error;
  const upgradeRequired = error instanceof ApiError && error.status === 402;

  return (
    <Card className="space-y-3">
      <CardTitle>AI-разбор тренера</CardTitle>
      {upgradeRequired ? (
        <>
          <p className="text-sm text-muted">
            Бесплатная проба AI-разбора использована. Оформи Pro для безлимитного разбора по
            поворотам, топ-ошибок и плана тренировки.
          </p>
          <Link href="/account">
            <Button>Перейти на Pro</Button>
          </Link>
        </>
      ) : (
        <>
          <p className="text-sm text-muted">
            Разбор круга по поворотам, топ-3 ошибки и план тренировки.
            {user?.plan !== "pro" && " Доступна 1 бесплатная проба."}
          </p>
          {error && (
            <p className="text-sm text-negative">
              {error instanceof ApiError ? error.message : "Не удалось разобрать круг"}
            </p>
          )}
          <Button onClick={onAnalyze} disabled={analyze.isPending}>
            {analyze.isPending ? "Разбираем…" : "Разобрать круг"}
          </Button>
        </>
      )}
    </Card>
  );
}
