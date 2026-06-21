"use client";

import Link from "next/link";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { cn } from "@/lib/cn";
import { fmtLapTime } from "@/lib/format";
import { useCoachTrajectory } from "@/lib/queries";
import type { TrajectoryLesson } from "@/lib/types";

const CYAN = "#22d3ee";

function Header() {
  return (
    <div>
      <h1 className="font-display text-3xl font-semibold tracking-tight">Тренер</h1>
      <p className="mt-1 text-sm text-muted">
        Траектория обучения: каждый разбор — урок с заданием, следующий проверяет, как ты его
        выполнил. Здесь виден весь прогресс по трассам.
      </p>
    </div>
  );
}

/** Tiny lap-time progression sparkline (faster = higher). */
function Sparkline({ times }: { times: number[] }) {
  if (times.length < 2) return null;
  const W = 220;
  const H = 44;
  const min = Math.min(...times);
  const max = Math.max(...times);
  const span = max - min || 1;
  const pts = times.map((t, i) => {
    const x = (i / (times.length - 1)) * W;
    const y = H - 4 - ((max - t) / span) * (H - 8); // lower time → higher point
    return [x, y] as const;
  });
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-11 w-[220px]" preserveAspectRatio="none">
      <path d={d} fill="none" stroke={CYAN} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === pts.length - 1 ? 3.5 : 2} fill={CYAN} />
      ))}
    </svg>
  );
}

function VerdictBadge({ verdict }: { verdict: "good" | "keep" }) {
  return (
    <span
      className={cn(
        "rounded-full px-2 py-0.5 text-[10px] font-medium",
        verdict === "good" ? "bg-positive/20 text-positive" : "bg-primary/20 text-primary",
      )}
    >
      {verdict === "good" ? "Прогресс!" : "Ещё поработай"}
    </span>
  );
}

function LessonNode({ lesson, n, prevTimeMs }: { lesson: TrajectoryLesson; n: number; prevTimeMs?: number }) {
  const s = lesson.summary;
  const delta = prevTimeMs != null ? (lesson.lap_time_ms - prevTimeMs) / 1000 : null;
  const date = new Date(lesson.recorded_at).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
  });

  return (
    <li className="relative pl-8">
      {/* timeline dot + line */}
      <span className="absolute left-0 top-1 grid h-6 w-6 place-items-center rounded-full border border-border bg-surface-2 font-mono text-[11px] text-muted">
        {n}
      </span>

      <div className="rounded-xl border border-border bg-surface p-4">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Link href={`/laps/${lesson.lap_id}`} className="font-display text-base font-semibold tabular-nums transition hover:text-primary">
            {fmtLapTime(lesson.lap_time_ms)}
          </Link>
          {delta != null && (
            <span className={cn("text-xs font-medium tabular-nums", delta <= 0 ? "text-positive" : "text-negative")}>
              {delta <= 0 ? "↓ " : "↑ +"}
              {Math.abs(delta).toFixed(2)} с
            </span>
          )}
          <span className="ml-auto text-xs text-muted">{date}</span>
        </div>

        {s.review && (
          <div className="mt-3 rounded-lg border border-border/70 bg-surface-2 p-3">
            <div className="mb-1 flex items-center gap-2 text-xs font-semibold">
              <span>📋 Проверка прошлого задания</span>
              <span className="ml-auto" />
              <VerdictBadge verdict={s.review.verdict} />
            </div>
            {s.review.text && <p className="text-sm text-muted">{s.review.text}</p>}
            {s.review.items.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm">
                {s.review.items.map((it, i) => (
                  <li key={i} className="flex gap-2">
                    <span>{it.improved === true ? "✅" : it.improved === false ? "🔸" : "•"}</span>
                    <span className={it.improved ? "text-positive" : "text-foreground"}>{it.note}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {s.focus_points && s.focus_points.length > 0 && (
          <div className="mt-3">
            <div className="mb-1 text-xs font-semibold" style={{ color: CYAN }}>
              🎯 Задание на эту сессию
            </div>
            <ul className="space-y-1">
              {s.focus_points.map((fp, i) => (
                <li key={i} className="text-sm">
                  <span className="font-medium">{fp.title}</span>{" "}
                  <span className="text-muted">— {fp.target}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </li>
  );
}

function TrackTrajectory({ track, lessons }: { track: string; lessons: TrajectoryLesson[] }) {
  const times = lessons.map((l) => l.lap_time_ms);
  const best = Math.min(...times);
  const first = times[0];
  const gainToBest = (first - best) / 1000; // how much faster your best is than your first lesson

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <CardTitle>{track}</CardTitle>
        <span className="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-muted">
          {lessons.length} {lessons.length === 1 ? "урок" : lessons.length < 5 ? "урока" : "уроков"}
        </span>
        <span className="text-xs text-muted">
          лучший <span className="font-mono text-foreground">{fmtLapTime(best)}</span>
        </span>
        {lessons.length > 1 && gainToBest > 0.05 && (
          <span className="text-xs font-medium text-positive">
            прогресс −{gainToBest.toFixed(2)} с от первого урока
          </span>
        )}
        <div className="ml-auto">
          <Sparkline times={times} />
        </div>
      </div>

      <ol className="mt-4 space-y-3 border-l border-border pl-0">
        {lessons.map((l, i) => (
          <LessonNode key={l.report_id} lesson={l} n={i + 1} prevTimeMs={i > 0 ? times[i - 1] : undefined} />
        ))}
      </ol>
    </Card>
  );
}

export default function TrainingPage() {
  const { data, isLoading } = useCoachTrajectory();

  if (isLoading) return <Spinner label="Загрузка траектории…" />;
  const lessons = data ?? [];

  if (lessons.length === 0) {
    return (
      <div className="space-y-6">
        <Header />
        <Card className="p-6 text-sm text-muted">
          Пока нет ни одного разбора. Открой любой круг и нажми{" "}
          <span className="text-foreground">«Разобрать круг»</span> — тренер даст первое задание, и
          здесь появится твоя траектория обучения с проверкой прогресса.
        </Card>
      </div>
    );
  }

  // Group lessons by track, preserving chronological order within each.
  const byTrack = new Map<string, TrajectoryLesson[]>();
  for (const l of lessons) {
    const key = l.track ?? "Без трассы";
    const arr = byTrack.get(key);
    if (arr) arr.push(l);
    else byTrack.set(key, [l]);
  }
  // Show the track with the most recent activity first.
  const tracks = [...byTrack.entries()].sort(
    (a, b) =>
      new Date(b[1][b[1].length - 1].recorded_at).getTime() -
      new Date(a[1][a[1].length - 1].recorded_at).getTime(),
  );

  const latest = lessons[lessons.length - 1];
  const homework = latest.summary.focus_points ?? [];

  return (
    <div className="space-y-6">
      <Header />

      {homework.length > 0 && (
        <Card className="border-[#22d3ee]/40 bg-[#22d3ee]/5 p-5">
          <div className="flex items-center gap-2">
            <CardTitle style={{ color: CYAN }}>🎯 Задание сейчас</CardTitle>
            {latest.track && <span className="ml-auto text-xs text-muted">{latest.track}</span>}
          </div>
          <ul className="mt-3 space-y-2">
            {homework.map((fp, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium">{fp.title}</span>{" "}
                <span className="text-muted">— {fp.target}</span>
              </li>
            ))}
          </ul>
          <Link
            href={`/laps/${latest.lap_id}`}
            className="mt-3 inline-block text-xs text-muted underline-offset-2 transition hover:text-foreground hover:underline"
          >
            из урока на {latest.track} →
          </Link>
        </Card>
      )}

      {tracks.map(([track, ls]) => (
        <TrackTrajectory key={track} track={track} lessons={ls} />
      ))}
    </div>
  );
}
