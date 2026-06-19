"use client";

import Link from "next/link";
import { useState } from "react";
import { TrackMap } from "@/components/TrackMap";
import { useAuth } from "@/lib/auth";

const STEPS = [
  {
    n: "1",
    title: "Поставь клиент",
    text: "Десктоп-клиент читает телеметрию F1 по UDP. Включи UDP в настройках игры — и всё готово.",
  },
  {
    n: "2",
    title: "Проедь круг",
    text: "Клиент сам ловит круги и отправляет в облако. Ничего не нужно нажимать во время заезда.",
  },
  {
    n: "3",
    title: "Получи разбор",
    text: "Графики, сравнение с твоим лучшим кругом и AI-разбор по поворотам: где и сколько теряешь.",
  },
];

const FEATURES = [
  { dot: "#f4f6fb", title: "Графики педалей и руля", text: "Скорость, газ, тормоз, руль и передачи по дистанции круга — плотно, но читаемо." },
  { dot: "#5a626e", title: "Сравнение с эталоном", text: "Наложение твоего лучшего круга поверх и дельта-график «где теряешь время»." },
  { dot: "#ff2d46", title: "AI-разбор по поворотам", text: "Топ-3 ошибки по стоимости времени и план тренировки. Понятно, на русском." },
  { dot: "#3ddc84", title: "Карта трассы с секторами", text: "Видно, на каком участке круга уходят десятые и сотые." },
  { dot: "#8b7bff", title: "Метрики каждого поворота", text: "Точка торможения, трейл-брейкинг, плавность руля, скорость в апексе." },
  { dot: "#f5a524", title: "Работает с консолью", text: "F1 шлёт телеметрию по UDP в сеть — клиент на ПК её ловит даже с PlayStation и Xbox." },
];

const PLANS = [
  { id: "free", title: "Free", price: "0 ₽", features: ["До 30 кругов в месяц", "Графики телеметрии", "Сравнение со своим лучшим", "1 пробный AI-разбор"], highlight: false },
  { id: "pro_m", title: "Pro — месяц", price: "690 ₽", per: "/мес", features: ["Безлимит кругов", "Безлимитный AI-разбор", "Полная история и прогресс"], highlight: true },
  { id: "pro_y", title: "Pro — год", price: "5 900 ₽", per: "/год", features: ["Всё из Pro", "2 месяца в подарок", "Приоритетная поддержка"], highlight: false },
];

const FAQ = [
  { q: "Какие игры поддерживаются?", a: "На старте — F1 24 и F1 25 по UDP. Дальше планируем Assetto Corsa и iRacing." },
  { q: "Работает ли на консоли?", a: "Да. F1 умеет слать телеметрию по UDP в локальную сеть — клиент на ПК её ловит, даже если ты играешь с PlayStation или Xbox." },
  { q: "Нужна ли мощная видеокарта?", a: "Нет. Анализ идёт в облаке. Клиент почти не нагружает ПК и не мешает игре." },
  { q: "Это безопасно?", a: "Клиент только читает телеметрию и отправляет её по HTTPS. Никакого доступа к самой игре или файлам." },
  { q: "Как отменить подписку?", a: "В любой момент в личном кабинете, в один клик. Доступ сохранится до конца оплаченного периода." },
];

function SpeedSpark() {
  const pts =
    "0,20 18,16 36,15 54,58 72,62 90,26 108,18 126,15 144,55 162,40 180,18 198,16 216,60 234,30 252,16 270,15 288,22 300,20";
  return (
    <svg viewBox="0 0 300 90" className="w-full" preserveAspectRatio="none" style={{ height: 96 }}>
      <defs>
        <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#f4f6fb" stopOpacity="0.18" />
          <stop offset="1" stopColor="#f4f6fb" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`${pts} 300,90 0,90`} fill="url(#spark)" />
      <polyline points={pts} fill="none" stroke="#f4f6fb" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

function ProductMock() {
  return (
    <div className="rounded-3xl border border-border bg-surface/80 p-4 shadow-2xl backdrop-blur">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="font-display text-lg font-semibold tracking-tight">Sim Circuit</span>
        <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1 text-xs">
          <span className="h-1.5 w-1.5 rounded-full bg-[#f4f6fb]" />
          <span className="text-muted">Твой круг</span>
          <span className="font-display font-semibold">1:13.84</span>
        </span>
        <span className="rounded-full border border-primary/40 bg-primary/10 px-3 py-1 font-display text-xs font-semibold text-primary">
          Δ +0.42
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2 rounded-2xl border border-border bg-surface p-3">
          <div className="mb-1 flex items-center gap-2 text-xs">
            <span className="h-2 w-2 rounded-full bg-[#f4f6fb]" />
            <span className="text-foreground">Скорость</span>
            <span className="ml-auto font-mono text-[10px] uppercase tracking-widest text-muted">км/ч</span>
          </div>
          <SpeedSpark />
        </div>
        <div className="rounded-2xl border border-border bg-surface p-3">
          <div className="mb-1 text-xs text-muted">Карта</div>
          <TrackMap progress={0.62} />
        </div>
      </div>
    </div>
  );
}

function Header({ ctaHref, ctaLabel, authed }: { ctaHref: string; ctaLabel: string; authed: boolean }) {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3.5">
        <Link href="/" className="flex items-center gap-2">
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-[#ff2d46] to-[#ff5b73]">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M7 17 L14 10" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
              <circle cx="15.5" cy="8.5" r="1.7" fill="#fff" />
            </svg>
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">
            <span className="text-primary">Apex</span>AI
          </span>
        </Link>
        <nav className="hidden gap-6 text-sm text-muted md:flex">
          <a href="#how" className="transition hover:text-foreground">Как работает</a>
          <a href="#features" className="transition hover:text-foreground">Возможности</a>
          <a href="#pricing" className="transition hover:text-foreground">Цены</a>
          <a href="#faq" className="transition hover:text-foreground">FAQ</a>
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {!authed && (
            <Link href="/login" className="hidden text-sm text-muted transition hover:text-foreground sm:block">
              Войти
            </Link>
          )}
          <Link
            href={ctaHref}
            className="rounded-full bg-gradient-to-r from-[#ff2d46] to-[#ff5b73] px-4 py-2 text-sm font-medium text-white shadow-[0_6px_24px_-8px_rgba(255,45,70,0.7)] transition hover:brightness-110"
          >
            {ctaLabel}
          </Link>
        </div>
      </div>
    </header>
  );
}

function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="mx-auto max-w-3xl px-6 py-20">
      <h2 className="mb-8 text-center font-display text-3xl font-semibold tracking-tight">Вопросы и ответы</h2>
      <div className="space-y-3">
        {FAQ.map((item, i) => (
          <div key={i} className="overflow-hidden rounded-2xl border border-border bg-surface">
            <button
              type="button"
              onClick={() => setOpen(open === i ? null : i)}
              className="flex w-full items-center gap-4 px-5 py-4 text-left"
            >
              <span className="font-medium">{item.q}</span>
              <span className={`ml-auto text-muted transition ${open === i ? "rotate-45 text-primary" : ""}`}>+</span>
            </button>
            {open === i && <p className="px-5 pb-4 text-sm text-muted">{item.a}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function Landing() {
  const { status } = useAuth();
  const authed = status === "authed";
  const ctaHref = authed ? "/dashboard" : "/login";
  const ctaLabel = authed ? "Открыть кабинет" : "Начать бесплатно";

  return (
    <div className="relative">
      <Header ctaHref={ctaHref} ctaLabel={ctaLabel} authed={authed} />

      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-2 lg:py-24">
        <div>
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" /> F1 24 / F1 25 · по UDP
          </div>
          <h1 className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-6xl">
            Найди, где ты теряешь <span className="text-primary">секунды</span>
          </h1>
          <p className="mt-5 max-w-md text-lg text-muted">
            AI-тренер разбирает твою телеметрию F1 по поворотам и понятно объясняет, что
            исправить. На русском. Бесплатно для старта.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href={ctaHref}
              className="rounded-full bg-gradient-to-r from-[#ff2d46] to-[#ff5b73] px-6 py-3 font-medium text-white shadow-[0_8px_30px_-8px_rgba(255,45,70,0.8)] transition hover:brightness-110"
            >
              {ctaLabel}
            </Link>
            <a href="#how" className="rounded-full border border-border px-6 py-3 text-sm text-foreground transition hover:border-muted">
              Как это работает
            </a>
          </div>
          <p className="mt-4 font-mono text-xs text-muted">Без карты · вход за 30 секунд</p>
        </div>
        <ProductMock />
      </section>

      {/* How it works */}
      <section id="how" className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="mb-3 text-center font-display text-3xl font-semibold tracking-tight">Как это работает</h2>
        <p className="mx-auto mb-12 max-w-md text-center text-muted">Три шага от заезда до разбора.</p>
        <div className="grid gap-5 md:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="rounded-2xl border border-border bg-surface p-6">
              <div className="mb-4 grid h-10 w-10 place-items-center rounded-xl border border-primary/40 bg-primary/10 font-display text-lg font-semibold text-primary">
                {s.n}
              </div>
              <h3 className="font-display text-lg font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm text-muted">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="mb-3 text-center font-display text-3xl font-semibold tracking-tight">Телеметрия, которая понятна</h2>
        <p className="mx-auto mb-12 max-w-md text-center text-muted">Серьёзность моторспорта без перегруза приборной панели.</p>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl border border-border bg-surface p-5">
              <span className="mb-3 inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: f.dot, boxShadow: `0 0 10px ${f.dot}` }} />
              <h3 className="font-medium">{f.title}</h3>
              <p className="mt-1.5 text-sm text-muted">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="mb-3 text-center font-display text-3xl font-semibold tracking-tight">Цены</h2>
        <p className="mx-auto mb-12 max-w-md text-center text-muted">Бесплатный старт. Pro — по цене для СНГ.</p>
        <div className="grid gap-5 md:grid-cols-3">
          {PLANS.map((p) => (
            <div
              key={p.id}
              className={`flex flex-col rounded-2xl border p-6 ${p.highlight ? "border-primary/50 bg-primary/5 shadow-[0_20px_60px_-30px_rgba(255,45,70,0.6)]" : "border-border bg-surface"}`}
            >
              <div className="text-sm font-semibold text-muted">{p.title}</div>
              <div className="mt-2 font-display text-3xl font-semibold">
                {p.price}
                {p.per && <span className="text-base font-normal text-muted">{p.per}</span>}
              </div>
              <ul className="mt-4 flex-1 space-y-2 text-sm text-muted">
                {p.features.map((feat) => (
                  <li key={feat} className="flex gap-2">
                    <span className="text-primary">›</span>
                    {feat}
                  </li>
                ))}
              </ul>
              <Link
                href={ctaHref}
                className={`mt-6 rounded-full px-5 py-2.5 text-center text-sm font-medium transition ${p.highlight ? "bg-gradient-to-r from-[#ff2d46] to-[#ff5b73] text-white hover:brightness-110" : "border border-border text-foreground hover:border-muted"}`}
              >
                {p.id === "free" ? "Начать бесплатно" : "Выбрать Pro"}
              </Link>
            </div>
          ))}
        </div>
      </section>

      <Faq />

      {/* Final CTA */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="relative overflow-hidden rounded-3xl border border-border bg-surface p-12 text-center">
          <div
            className="pointer-events-none absolute inset-0"
            style={{ background: "radial-gradient(60% 120% at 50% 120%, rgba(255,45,70,0.22), transparent 70%)" }}
          />
          <div className="relative">
            <h2 className="font-display text-4xl font-bold tracking-tight">Готов стать быстрее?</h2>
            <p className="mx-auto mt-3 max-w-md text-muted">
              Проедь круг, и AI-тренер покажет, где спрятались твои секунды.
            </p>
            <Link
              href={ctaHref}
              className="mt-8 inline-block rounded-full bg-gradient-to-r from-[#ff2d46] to-[#ff5b73] px-7 py-3 font-medium text-white shadow-[0_8px_30px_-8px_rgba(255,45,70,0.8)] transition hover:brightness-110"
            >
              {ctaLabel}
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10 sm:flex-row sm:items-center">
          <div>
            <div className="font-display text-lg font-semibold tracking-tight">
              <span className="text-primary">Apex</span>AI
            </div>
            <p className="mt-1 text-sm text-muted">AI-тренер по симрейсингу F1.</p>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted sm:ml-auto">
            <a href="#features" className="transition hover:text-foreground">Возможности</a>
            <a href="#pricing" className="transition hover:text-foreground">Цены</a>
            <a href="#faq" className="transition hover:text-foreground">FAQ</a>
            <a href="#" className="transition hover:text-foreground">Discord</a>
            <a href="#" className="transition hover:text-foreground">Оферта</a>
            <a href="#" className="transition hover:text-foreground">Политика</a>
          </div>
        </div>
        <div className="border-t border-border/60 px-6 py-4 text-center font-mono text-xs text-muted">
          © 2026 ApexAI
        </div>
      </footer>
    </div>
  );
}
