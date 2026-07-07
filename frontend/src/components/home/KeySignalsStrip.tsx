import type { ListeningMinutes, ScoreMetric } from "../../types/api";
import { formatMinutes } from "../../utils/format";

interface Props {
  repeatScore: ScoreMetric;
  discoveryScore: ScoreMetric;
  nicheScore?: ScoreMetric;
  thisMonthMinutes: ListeningMinutes | null;
  rollingYearMinutes: ListeningMinutes | null;
}

export function KeySignalsStrip({ repeatScore, discoveryScore, nicheScore, thisMonthMinutes, rollingYearMinutes }: Props) {
  const signals = [
    {
      label: "Repeat-heavy listening",
      value: `${Math.round(repeatScore.value)}%`,
      text: "You come back to the same songs strongly once they land.",
    },
    {
      label: "Selective discovery",
      value: `${Math.round(discoveryScore.value)}%`,
      text: discoveryScore.interpretation?.plain_english ?? "You explore selectively, while known favourites still shape the centre.",
    },
    {
      label: "Niche estimate",
      value: nicheScore ? `${Math.round(nicheScore.value)}%` : "Unavailable",
      text: nicheScore?.interpretation?.plain_english ?? "Popularity metadata is too partial to make a strong reach claim.",
    },
    {
      label: "Detected listening time",
      value: thisMonthMinutes ? formatMinutes(thisMonthMinutes.metrics.current_month_total_minutes) : rollingYearMinutes ? formatMinutes(rollingYearMinutes.metrics.rolling_365_total_minutes) : "Unavailable",
      text: thisMonthMinutes
        ? `This month, estimated from detected track durations with ${thisMonthMinutes.duration_quality.duration_coverage_percent}% coverage.`
        : "Estimated from detected track durations when duration data is available.",
    },
  ];

  return (
    <section className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 md:grid-cols-2 xl:grid-cols-4">
      {signals.map((signal, index) => (
        <article key={signal.label} className="group bg-ink/84 p-5 transition hover:bg-panelSoft">
          <div className="flex items-start justify-between gap-4">
            <p className="text-sm font-semibold text-white">{signal.label}</p>
            <span className="text-xs text-violet-200">0{index + 1}</span>
          </div>
          <p className="mt-4 text-3xl font-black text-white">{signal.value}</p>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-mist">{signal.text}</p>
          <div className="mt-5 h-px w-12 bg-gradient-to-r from-violet to-transparent transition group-hover:w-24" />
        </article>
      ))}
    </section>
  );
}
