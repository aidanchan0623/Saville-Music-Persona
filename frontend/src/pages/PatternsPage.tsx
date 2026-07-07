import { ChartPanel } from "../components/ChartPanel";
import { EmptyState } from "../components/EmptyState";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Charts, ListeningMinutes } from "../types/api";
import { formatMinutes } from "../utils/format";

export function PatternsPage({ charts }: { charts: Charts | null }) {
  const [period, setPeriod] = useState("last_30");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [minutes, setMinutes] = useState<ListeningMinutes | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.listeningMinutes(period, period === "month" ? selectedMonth : null)
      .then((next) => {
        if (cancelled) return;
        setMinutes(next);
        if (!selectedMonth && next.period.available_months.length) setSelectedMonth(next.period.available_months[next.period.available_months.length - 1].value);
      })
      .catch(() => {
        if (!cancelled) setMinutes(null);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth]);

  if (!charts) return <EmptyState title="No listening patterns yet" body="Refresh data to build charts from local cached analysis." />;
  const months = minutes?.period.available_months ?? [];
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-bold text-white">Listening Patterns</h1>
        <p className="mt-2 text-mist">Charts stay tied to real available fields; the timeline appears only when play dates are parseable.</p>
      </div>

      <section className="rounded-lg border border-violet/20 bg-panel/82 p-5 shadow-glow">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.16em] text-violet-200">Daily Listening Minutes</p>
            <h2 className="mt-1 text-2xl font-black text-white">{minutes?.period.label ?? "Selected period"}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
              Detected listening minutes are estimated from full track durations. Missing days are preserved as zero so quiet periods stay visible.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              ["last_7", "Last 7 days"],
              ["last_30", "Last 30 days"],
              ["this_month", "Current month"],
              ["month", "Select month"],
              ["rolling_year", "Rolling 365"],
              ["all", "All history"],
            ].map(([value, label]) => (
              <button key={value} className={`rounded-md px-3 py-2 text-sm font-semibold ${period === value ? "bg-violet text-white" : "bg-white/10 text-mist hover:text-white"}`} onClick={() => setPeriod(value)}>
                {label}
              </button>
            ))}
            {period === "month" ? (
              <select className="rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-white" value={selectedMonth ?? months[months.length - 1]?.value ?? ""} onChange={(event) => setSelectedMonth(event.target.value)}>
                {months.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
              </select>
            ) : null}
          </div>
        </div>
        {minutes ? (
          <>
            <div className="mt-5 grid gap-3 md:grid-cols-4">
              <MinuteStat label="Selected total" value={formatMinutes(minutes.metrics.selected_period_total_minutes)} caption={`${minutes.duration_quality.duration_coverage_percent}% duration coverage`} />
              <MinuteStat label="Average active day" value={formatMinutes(minutes.metrics.average_active_day_minutes)} caption={`${minutes.metrics.active_listening_days} active days`} />
              <MinuteStat label="Longest day" value={minutes.metrics.longest_detected_listening_day?.formatted ?? "Unavailable"} caption={minutes.metrics.longest_detected_listening_day?.date ?? "No usable duration"} />
              <MinuteStat label="Current streak" value={`${minutes.metrics.current_listening_streak_days} days`} caption="Active day = at least one detected music play" />
            </div>
            <p className="mt-4 rounded-md bg-white/[0.04] p-3 text-sm text-mist">{minutes.summary_sentence}</p>
            <div className="mt-5 grid gap-5 xl:grid-cols-3">
              <ChartPanel title="Daily detected minutes" data={minutes.daily} type="line" />
              <ChartPanel title="Weekly aggregate minutes" data={minutes.weekly} />
              <ChartPanel title="Monthly aggregate minutes" data={minutes.monthly} />
            </div>
            <Heatmap values={minutes.heatmap.slice(-140)} />
          </>
        ) : (
          <div className="mt-5 rounded-md bg-white/[0.03] p-5 text-sm text-mist">No minute analytics available yet.</div>
        )}
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <ChartPanel title="Listening by release decade" data={charts.release_decades} />
        <ChartPanel title="Top genre clusters" data={charts.top_genre_clusters} type="pie" />
        <ChartPanel title="Top artists by detected plays" data={charts.top_artists} />
        <ChartPanel title="Most repeated songs" data={charts.most_repeated_songs} />
        <ChartPanel title="Artist concentration" data={charts.artist_concentration} type="pie" />
        <ChartPanel title="Playlist influence" data={charts.playlist_influence} />
        <div className="xl:col-span-2">
          <ChartPanel title="Data coverage timeline" data={charts.coverage_timeline} type="line" />
        </div>
      </div>
    </div>
  );
}

function MinuteStat({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <div className="rounded-md bg-white/[0.05] p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-mist/60">{label}</p>
      <p className="mt-2 text-xl font-black text-white">{value}</p>
      <p className="mt-1 text-xs text-mist">{caption}</p>
    </div>
  );
}

function Heatmap({ values }: { values: ListeningMinutes["heatmap"] }) {
  if (!values.length) return null;
  const max = Math.max(...values.map((item) => item.value), 1);
  return (
    <div className="mt-5 rounded-md bg-white/[0.04] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-white">Recent daily intensity</h3>
        <p className="text-xs text-mist">Darker cells mean more detected minutes.</p>
      </div>
      <div className="grid gap-1 overflow-x-auto pb-1" style={{ gridTemplateColumns: "repeat(20, minmax(1rem, 1rem))" }}>
        {values.map((item) => {
          const opacity = Math.max(0.08, item.value / max);
          return (
            <span
              key={item.date}
              title={`${item.date}: ${item.value} detected minutes`}
              className="h-4 min-w-4 rounded-sm border border-white/5"
              style={{ backgroundColor: `rgba(167, 139, 250, ${opacity})` }}
            />
          );
        })}
      </div>
    </div>
  );
}
