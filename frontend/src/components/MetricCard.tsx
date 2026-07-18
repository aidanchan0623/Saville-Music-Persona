import type { ReactNode } from "react";

interface Props {
  label: string;
  value: ReactNode;
  caption?: string;
  accent?: "red" | "deep" | "soft";
}

export function MetricCard({ label, value, caption, accent = "red" }: Props) {
  const accents = {
    red: "from-red-500/20 to-red-500/0 text-red-100",
    deep: "from-red-950/35 to-red-950/0 text-red-100",
    soft: "from-white/[0.075] to-white/[0.015] text-mist",
  };
  return (
    <section className={`rounded-lg border border-line bg-gradient-to-br ${accents[accent]} p-5 shadow-glow`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist/70">{label}</p>
      <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
      {caption ? <p className="mt-2 text-sm leading-6 text-mist">{caption}</p> : null}
    </section>
  );
}
