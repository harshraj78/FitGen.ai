import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function money(value?: number | null, currency = "Rs") {
  return `${currency} ${Math.round(Number(value) || 0).toLocaleString()}`;
}

export function percent(value?: number | null) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

export function label(value?: string | null) {
  return String(value || "").replace(/_/g, " ");
}
