import type { ReactNode } from "react";

interface MetricBlockProps {
  label: string;
  value: ReactNode;
  caption?: ReactNode;
  index?: number;
  tone?: "red" | "neutral" | "green" | "amber";
}

export function MetricBlock({ label, value, caption, index, tone = "red" }: MetricBlockProps) {
  const toneClass = {
    red: "from-red-500/18 to-red-950/5 text-red-100",
    neutral: "from-white/[0.075] to-white/[0.02] text-white",
    green: "from-emerald-400/14 to-emerald-950/5 text-emerald-100",
    amber: "from-amber-300/15 to-amber-950/5 text-amber-100",
  }[tone];

  return (
    <article className={`relative overflow-hidden rounded-lg border border-white/10 bg-gradient-to-br ${toneClass} p-4`}>
      {typeof index === "number" ? <span className="absolute right-4 top-3 font-display text-3xl leading-none text-white/[0.035]">{String(index).padStart(2, "0")}</span> : null}
      <p className="text-xs font-semibold uppercase tracking-[0.17em] text-mist/60">{label}</p>
      <div className="mt-3 text-2xl font-black leading-tight text-white md:text-3xl">{value}</div>
      {caption ? <p className="mt-2 text-sm leading-6 text-mist">{caption}</p> : null}
    </article>
  );
}
