import { cn } from "@/lib/cn";

/** Pill toggle with an optional colored channel dot (telemetry channel chips, filters). */
export function Chip({
  active = false,
  color,
  onClick,
  className,
  children,
}: {
  active?: boolean;
  color?: string;
  onClick?: () => void;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm transition",
        active
          ? "border-border bg-surface-2 text-foreground"
          : "border-border/60 bg-surface/40 text-muted hover:text-foreground",
        className,
      )}
    >
      {color && (
        <span
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: color, boxShadow: active ? `0 0 8px ${color}` : "none" }}
        />
      )}
      {children}
    </button>
  );
}
