import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${className}`}
    >
      {children}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <Card>
      <div className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </Card>
  );
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const base =
    "inline-flex items-center justify-center rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-brand text-white hover:bg-brand-dark"
      : "border border-slate-300 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800";
  // className must come AFTER the spread's would-be position so callers extend, not replace, styling.
  return (
    <button className={`${base} ${styles} ${className}`} {...props}>
      {children}
    </button>
  );
}

const bandColors: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  high: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
  critical: "bg-rose-200 text-rose-800",
};

export function Badge({ label }: { label: string }) {
  const cls = bandColors[label.toLowerCase()] ?? "bg-slate-100 text-slate-700 dark:bg-slate-800";
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>{label}</span>;
}
