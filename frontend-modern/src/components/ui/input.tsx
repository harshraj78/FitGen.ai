import * as React from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-10 rounded-md border bg-card px-3 text-sm outline-none ring-primary/20 transition focus:ring-4",
        className,
      )}
      {...props}
    />
  );
}
