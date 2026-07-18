import { ChartPanel } from "../components/ChartPanel";
import { EmptyState } from "../components/EmptyState";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { AnimatedPageTitle } from "../components/AnimatedPageTitle";
import { GlowPanel } from "../components/GlowPanel";
import type { Charts, ListeningMinutes, MusicSource } from "../types/api";
import { formatMinutes } from "../utils/format";

export function PatternsPage({ charts, source, titleAnimationKey }: { charts: Charts | null; source: MusicSource; titleAnimationKey: string }) {
  const [period, setPeriod] = useState<"this_month" | "month" | "rolling_year">("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [minutes, setMinutes] = useState<ListeningMinutes | null>(null);
  const [periodCharts, setPeriodCharts] = useState<Charts | null>(charts);

  useEffect(() => setPeriodCharts(charts), [charts]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.listeningMinutes(period, period === "month" ? selectedMonth : null, source),
      api.charts(period, period === "month" ? selectedMonth : null, source),
    ])
      .then(([next, nextCharts]) => {
        if (cancelled) return;
        setMinutes(next);
        setPeriodCharts(nextCharts);
        if (!selectedMonth && next.period.available_months.length) setSelectedMonth(next.period.available_months[next.period.available_months.length - 1].value);
      })
      .catch(() => {
        if (!cancelled) setMinutes(null);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth, source]);

  if (!charts) return <EmptyState title="No listening patterns yet" body="Refresh data to build charts from local cached analysis." titleTag="h1" titleAnimationKey={titleAnimationKey} />;
  const months = minutes?.period.available_months ?? [];
  const activeCharts = periodCharts ?? charts;
  const activeLabel = period === "rolling_year" ? "Rolling Year" : minutes?.period.label ?? "Selected period";
  return (
    <div className="space-y-5">
      <div>
        <AnimatedPageTitle animationKey={titleAnimationKey} text="Listening Patterns" className="text-3xl font-bold text-white" />
        <p className="mt-2 text-mist">
          {source === "spotify" ? "Charts follow Spotify top-item, saved-library, playlist, and recent-sync signals available locally." : "Charts follow the dates and music details available in your local history."}
        </p>
      </div>

      <GlowPanel as="section" variant="major" lined className="p-4 md:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.16em] text-red-200">Daily Listening Minutes</p>
            <h2 className="mt-1 text-2xl font-black text-white">{activeLabel}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
              A practical view of when you listened most, with quiet days kept visible instead of smoothed away.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {([
              ["this_month", "This Month"],
              ["month", "Select Month"],
              ["rolling_year", "Rolling Year"],
            ] as const).map(([value, label]) => (
              <button key={value} className={`rounded-md px-3 py-2 text-sm font-semibold ${period === value ? "bg-red-600 text-white" : "bg-white/10 text-mist hover:text-white"}`} onClick={() => setPeriod(value)}>
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
              <MinuteStat label="Selected total" value={formatMinutes(minutes.metrics.selected_period_total_minutes)} caption="Across the selected period" />
              <MinuteStat label="Average active day" value={formatMinutes(minutes.metrics.average_active_day_minutes)} caption={`${minutes.metrics.active_listening_days} active days`} />
              <MinuteStat label="Longest day" value={minutes.metrics.longest_detected_listening_day?.formatted ?? "Unavailable"} caption={minutes.metrics.longest_detected_listening_day?.date ?? "No listening time yet"} />
              <MinuteStat label="Current streak" value={`${minutes.metrics.current_listening_streak_days} days`} caption="Active day = at least one detected music play" />
            </div>
            <GlowPanel as="p" variant="row" wrapperClassName="mt-4" className="p-3 text-sm text-mist">{minutes.summary_sentence}</GlowPanel>
            <div className="mt-5 grid min-w-0 gap-4 xl:grid-cols-3">
              <ChartPanel title="Daily detected minutes" data={minutes.daily} type="line" />
              <ChartPanel title="Weekly aggregate minutes" data={minutes.weekly} />
              <ChartPanel title="Monthly aggregate minutes" data={minutes.monthly} />
            </div>
            <Heatmap values={minutes.heatmap.slice(-140)} />
          </>
        ) : (
          <GlowPanel as="div" variant="row" wrapperClassName="mt-5" className="p-5 text-sm text-mist">No minute analytics available yet.</GlowPanel>
        )}
      </GlowPanel>

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <ChartPanel title={`Listening by release decade - ${activeLabel}`} data={activeCharts.release_decades} />
        <ChartPanel title={`Dominant genre families - ${activeLabel}`} data={activeCharts.top_genre_clusters} type="pie" />
        <ChartPanel title={`Top artists by plays - ${activeLabel}`} data={activeCharts.top_artists} />
        <ChartPanel title={`Most repeated songs - ${activeLabel}`} data={activeCharts.most_repeated_songs} />
        <ChartPanel title={`Artist concentration - ${activeLabel}`} data={activeCharts.artist_concentration} type="pie" />
        <ChartPanel title={`Playlist influence - ${activeLabel}`} data={activeCharts.playlist_influence} />
        <div className="xl:col-span-2">
          <ChartPanel title={`Listening history timeline - ${activeLabel}`} data={activeCharts.coverage_timeline} type="line" />
        </div>
      </div>
    </div>
  );
}

function MinuteStat({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <GlowPanel as="div" variant="row" className="p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-mist/60">{label}</p>
      <p className="mt-2 text-xl font-black text-white">{value}</p>
      <p className="mt-1 text-xs text-mist">{caption}</p>
    </GlowPanel>
  );
}

function Heatmap({ values }: { values: ListeningMinutes["heatmap"] }) {
  if (!values.length) return null;
  const max = Math.max(...values.map((item) => item.value), 1);
  return (
    <GlowPanel as="div" variant="card" wrapperClassName="mt-5" className="p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-white">Recent daily intensity</h3>
        <p className="text-xs text-mist">Brighter red cells mean more detected listening time.</p>
      </div>
      <div className="grid gap-1 overflow-x-auto pb-1" style={{ gridTemplateColumns: "repeat(20, minmax(1rem, 1rem))" }}>
        {values.map((item) => {
          const opacity = Math.max(0.08, item.value / max);
          return (
            <span
              key={item.date}
              title={`${item.date}: ${item.value} detected minutes`}
              className="h-4 min-w-4 rounded-sm border border-white/5"
              style={{ backgroundColor: `rgba(239, 68, 68, ${opacity})` }}
            />
          );
        })}
      </div>
    </GlowPanel>
  );
}
