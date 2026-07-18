import type { ReactNode } from "react";
import { GlowPanel } from "./GlowPanel";

interface Props {
  label: string;
  value: ReactNode;
  caption?: string;
  accent?: "violet" | "indigo" | "magenta";
}

export function MetricCard({ label, value, caption, accent = "violet" }: Props) {
  const accents = {
    violet: "from-violet/20 to-violet/0 text-violet-100",
    indigo: "from-indigo/20 to-indigo/0 text-indigo-100",
    magenta: "from-magenta/20 to-magenta/0 text-red-100",
  };
  return (
    <GlowPanel as="section" variant="card" className={`bg-gradient-to-br ${accents[accent]} p-5`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist/70">{label}</p>
      <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
      {caption ? <p className="mt-2 text-sm leading-6 text-mist">{caption}</p> : null}
    </GlowPanel>
  );
}
