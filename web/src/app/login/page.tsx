"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { status, login, register } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "authed") router.replace("/dashboard");
  }, [status, router]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await register(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Что-то пошло не так");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen place-items-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-[#ff2d46] to-[#ff5b73] shadow-[0_6px_20px_-6px_rgba(255,45,70,0.8)]">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M7 17 L14 10" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
              <circle cx="15.5" cy="8.5" r="1.7" fill="#fff" />
            </svg>
          </div>
          <div className="font-display text-2xl font-semibold tracking-tight">
            <span className="text-primary">Apex</span>AI
          </div>
          <p className="mt-1 text-sm text-muted">AI-тренер по симрейсингу F1</p>
        </div>

        <form onSubmit={submit} className="space-y-3 rounded-2xl border border-border bg-surface p-6">
          <Input
            type="email"
            placeholder="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          <Input
            type="password"
            placeholder="пароль (от 8 символов)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
          {error && <p className="text-sm text-negative">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "…" : mode === "login" ? "Войти" : "Создать аккаунт"}
          </Button>
        </form>

        <p className="mt-4 text-center text-sm text-muted">
          {mode === "login" ? "Нет аккаунта?" : "Уже есть аккаунт?"}{" "}
          <button
            type="button"
            className="text-primary hover:underline"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login" ? "Регистрация" : "Войти"}
          </button>
        </p>
      </div>
    </div>
  );
}
