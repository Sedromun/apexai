"use client";

import Link from "next/link";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { useAnalyzeLap, useCoachReport } from "@/lib/queries";
import { Button } from "./ui/Button";
import { Card, CardTitle } from "./ui/Card";
import { Spinner } from "./ui/Spinner";

export function CoachPanel({ lapId }: { lapId: string }) {
  const { user, refreshUser } = useAuth();
  const { data: report, isLoading } = useCoachReport(lapId);
  const analyze = useAnalyzeLap();

  const run = async (force: boolean) => {
    try {
      await analyze.mutateAsync({ lapId, force });
      await refreshUser(); // reflect the spent AI trial in usage counters
    } catch {
      /* error surfaced from analyze.error below */
    }
  };
  const onAnalyze = () => run(false);
  const onRegenerate = () => run(true);

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
        <div className="flex items-center gap-3">
          <CardTitle>AI-разбор тренера</CardTitle>
          <span className="ml-auto font-mono text-[11px] text-muted">{report.model}</span>
          <button
            type="button"
            onClick={onRegenerate}
            disabled={analyze.isPending}
            title="Сгенерировать заново"
            className={cn(
              "rounded-full border border-border px-3 py-1 text-xs font-medium transition",
              analyze.isPending
                ? "cursor-not-allowed text-muted"
                : "text-foreground hover:border-primary/50 hover:text-primary",
            )}
          >
            {analyze.isPending ? "Генерирую…" : "↻ Перегенерировать"}
          </button>
        </div>
        {analyze.error && (
          <p className="text-sm text-negative">
            {analyze.error instanceof ApiError ? analyze.error.message : "Не удалось перегенерировать"}
          </p>
        )}
        <p className="text-sm">{s.summary_text}</p>

        {s.review && (
          <div
            className={cn(
              "rounded-lg border p-3",
              s.review.verdict === "good"
                ? "border-positive/40 bg-positive/5"
                : "border-primary/30 bg-primary/5",
            )}
          >
            <div className="mb-1 flex items-center gap-2 text-xs font-semibold">
              <span>📋 Проверка прошлого задания</span>
              <span
                className={cn(
                  "ml-auto rounded-full px-2 py-0.5 text-[10px]",
                  s.review.verdict === "good"
                    ? "bg-positive/20 text-positive"
                    : "bg-primary/20 text-primary",
                )}
              >
                {s.review.verdict === "good" ? "Прогресс!" : "Ещё поработай"}
              </span>
            </div>
            {s.review.text && <p className="text-sm">{s.review.text}</p>}
            {s.review.items.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm">
                {s.review.items.map((it, i) => (
                  <li key={i} className="flex gap-2">
                    <span>{it.improved === true ? "✅" : it.improved === false ? "🔸" : "•"}</span>
                    <span className={it.improved === true ? "text-positive" : "text-foreground"}>
                      {it.note}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {s.focus_points && s.focus_points.length > 0 && (
          <div className="rounded-lg border border-[#22d3ee]/40 bg-[#22d3ee]/5 p-3">
            <div className="mb-1.5 text-xs font-semibold text-[#22d3ee]">
              🎯 Задание на эту сессию
            </div>
            <ul className="space-y-2">
              {s.focus_points.map((fp, i) => (
                <li key={i} className="text-sm">
                  <span className="font-medium">{fp.title}</span>{" "}
                  <span className="text-muted">— {fp.target}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {s.top_mistakes.length > 0 && (
          <div>
            <div className="mb-1 text-xs font-semibold text-muted">Где теряешь время</div>
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
