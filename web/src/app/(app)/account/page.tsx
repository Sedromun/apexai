"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";
import { fmtDateTime, fmtPrice } from "@/lib/format";
import { usePlans, useSubscribe } from "@/lib/queries";

export default function AccountPage() {
  const { user } = useAuth();
  const { data: plans } = usePlans();
  const subscribe = useSubscribe();
  const [busyPlan, setBusyPlan] = useState<string | null>(null);

  const onSubscribe = async (plan: string) => {
    setBusyPlan(plan);
    try {
      const res = await subscribe.mutateAsync(plan);
      window.location.assign(res.checkout_url);
    } catch {
      setBusyPlan(null);
    }
  };

  if (!user) return <Spinner label="…" />;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-2xl font-semibold tracking-tight">Аккаунт и подписка</h1>

      <Card>
        <CardTitle>Текущий тариф</CardTitle>
        <div className="mt-2 flex items-center gap-3">
          <Badge
            className={user.plan === "pro" ? "bg-primary/15 text-primary" : "bg-surface-2 text-muted"}
          >
            {user.plan.toUpperCase()}
          </Badge>
          {user.plan === "pro" && user.subscription?.current_period_end && (
            <span className="text-sm text-muted">
              активна до {fmtDateTime(user.subscription.current_period_end)}
            </span>
          )}
        </div>
        <p className="mt-2 text-sm text-muted">
          Кругов за месяц: {user.usage.laps_this_month}
          {user.plan !== "pro" && ` / ${user.limits.free_monthly_lap_limit}`} · AI-разборов:{" "}
          {user.usage.ai_reports_used}
        </p>
      </Card>

      <div className="grid gap-3 sm:grid-cols-3">
        {plans?.map((plan) => (
          <Card key={plan.id} className="flex flex-col">
            <div className="text-sm font-semibold">{plan.title}</div>
            <div className="mt-1 font-display text-2xl font-semibold">{fmtPrice(plan.price_rub, plan.period)}</div>
            <ul className="mt-3 flex-1 space-y-1 text-sm text-muted">
              {plan.features.map((feature, i) => (
                <li key={i}>• {feature}</li>
              ))}
            </ul>
            <div className="mt-4">
              {plan.id === "free" ? (
                <Button variant="secondary" disabled className="w-full">
                  Базовый
                </Button>
              ) : user.plan === "pro" ? (
                <Button variant="secondary" disabled className="w-full">
                  Активно
                </Button>
              ) : (
                <Button
                  className="w-full"
                  onClick={() => onSubscribe(plan.id)}
                  disabled={busyPlan !== null}
                >
                  {busyPlan === plan.id ? "…" : "Оформить"}
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <CardTitle>Десктоп-клиент</CardTitle>
        <p className="mt-2 text-sm text-muted">
          Захват телеметрии F1 по UDP (Windows). В игре: Настройки → Телеметрия → UDP On,
          частота 60 Гц, IP 127.0.0.1.
        </p>
        <Button variant="secondary" className="mt-3" disabled>
          Скачать (скоро)
        </Button>
      </Card>
    </div>
  );
}
