import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary:
    "bg-gradient-to-r from-[#ff2d46] to-[#ff5b73] text-white shadow-[0_6px_24px_-8px_rgba(255,45,70,0.7)] hover:brightness-110",
  secondary: "border border-border bg-surface-2 text-foreground hover:border-muted",
  ghost: "text-muted hover:bg-surface-2 hover:text-foreground",
  danger: "bg-negative text-white hover:brightness-110",
};

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
