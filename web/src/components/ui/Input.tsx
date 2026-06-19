import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full rounded-md border border-border bg-surface-2 px-3 py-2 text-sm text-foreground outline-none transition placeholder:text-muted focus:border-primary",
          className,
        )}
        {...props}
      />
    );
  },
);
