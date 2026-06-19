export function fmtLapTime(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.floor((ms % 60_000) / 1000);
  const millis = Math.round(ms % 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}.${millis.toString().padStart(3, "0")}`;
}

export function fmtDelta(seconds: number): string {
  return `${seconds >= 0 ? "+" : ""}${seconds.toFixed(3)}`;
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtPrice(rub: number, period: string | null): string {
  if (rub === 0) return "Бесплатно";
  const suffix = period === "month" ? "/мес" : period === "year" ? "/год" : "";
  return `${rub.toLocaleString("ru-RU")} ₽${suffix}`;
}
