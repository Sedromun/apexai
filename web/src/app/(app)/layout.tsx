"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui/Spinner";
import { useAuth } from "@/lib/auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "anon") router.replace("/login");
  }, [status, router]);

  if (status !== "authed") {
    return (
      <div className="grid min-h-screen place-items-center">
        <Spinner label="Загрузка…" />
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
