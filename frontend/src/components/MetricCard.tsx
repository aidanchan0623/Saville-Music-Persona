import type { ReactNode } from "react";

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
    magenta: "from-magenta/20 to-magenta/0 text-fuchsia-100",
  };
  return (
    <section className={`rounded-lg border border-line bg-gradient-to-br ${accents[accent]} p-5 shadow-glow`}>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist/70">{label}</p>
      <div className="mt-3 text-3xl font-semibold text-white">{value}</div>
      {caption ? <p className="mt-2 text-sm leading-6 text-mist">{caption}</p> : null}
    </section>
  );
}

