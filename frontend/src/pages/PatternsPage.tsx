import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ChartPanel } from "../components/ChartPanel";
import { EmptyState } from "../components/EmptyState";
import { MetricBlock } from "../components/ui/MetricBlock";
import { PageHeader } from "../components/ui/PageHeader";
import { PeriodSelector, type PeriodValue, standardPeriodOptions } from "../components/ui/PeriodSelector";
import type { Charts, ListeningMinutes, MusicSource } from "../types/api";
import { formatMinutes } from "../utils/format";

export function PatternsPage({ charts, source }: { charts: Charts | null; source: MusicSource }) {
  const [period, setPeriod] = useState<PeriodValue>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [minutes, setMinutes] = useState<ListeningMinutes | null>(null);
  const [periodCharts, setPeriodCharts] = useState<Charts | null>(charts);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setPeriodCharts(charts), [charts]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
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
      .catch((nextError: Error) => {
        if (!cancelled) {
          setMinutes(null);
          setError(nextError.message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth, source]);

  const activeCharts = periodCharts ?? charts;
  if (!activeCharts) return <EmptyState title="No listening patterns yet" body="Refresh data to build charts from local cached analysis." />;

  const months = minutes?.period.available_months ?? [];
  const activeLabel = period === "rolling_year" ? "Rolling Year" : minutes?.period.label ?? periodLabel(period);

  return (
    <div className="space-y-9">
      <section className="editorial-panel overflow-hidden">
        <div className="p-5 md:p-8">
          <PageHeader
            eyebrow="Listening patterns"
            title="Patterns"
            description={source === "spotify" ? "Charts follow Spotify top-item, saved-library, playlist, and recent-sync signals available locally." : "Charts follow the dates, durations, and music details available in your local history."}
            action={<PeriodSelector value={period} onChange={setPeriod} month={selectedMonth} months={months} onMonthChange={setSelectedMonth} options={standardPeriodOptions} />}
            meta={
              <>
                <span className="subtle-pill border-red-400/20 bg-red-500/10 text-red-100">{activeLabel}</span>
                {loading ? <span className="subtle-pill">Updating</span> : null}
                {source === "spotify" ? <span className="subtle-pill">Spotify signal model</span> : null}
              </>
            }
          />
        </div>
        <div className="grid gap-px border-t border-white/10 bg-white/10 md:grid-cols-4">
          <MetricBlock label="Selected total" value={minutes ? formatMinutes(minutes.metrics.selected_period_total_minutes) : "Unavailable"} caption="Detected listening minutes" index={1} />
          <MetricBlock label="Average active day" value={minutes ? formatMinutes(minutes.metrics.average_active_day_minutes) : "Unavailable"} caption={minutes ? `${minutes.metrics.active_listening_days} active days` : "Waiting for period data"} index={2} />
          <MetricBlock label="Longest day" value={minutes?.metrics.longest_detected_listening_day?.formatted ?? "Unavailable"} caption={minutes?.metrics.longest_detected_listening_day?.date ?? "No listening time yet"} index={3} />
          <MetricBlock label="Current streak" value={`${minutes?.metrics.current_listening_streak_days ?? 0} days`} caption="Active day has at least one detected music play" index={4} />
        </div>
      </section>

      {error ? <p className="rounded-lg border border-red-300/10 bg-red-400/10 p-4 text-sm text-red-100">{error}</p> : null}

      <section className="editorial-panel p-5 md:p-7">
        <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="section-label">Detected listening time</p>
            <h2 className="mt-2 text-3xl font-black text-white">{activeLabel}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
              A practical view of when you listened most, with quiet days kept visible instead of smoothed away.
            </p>
          </div>
          {minutes?.duration_quality.confidence_badge ? <span className="subtle-pill">{minutes.duration_quality.confidence_badge}</span> : null}
        </div>
        {minutes ? (
          <>
            <p className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-mist">{minutes.summary_sentence}</p>
            <div className="mt-5 grid gap-5 xl:grid-cols-3">
              <ChartPanel title="Daily detected minutes" data={minutes.daily} type="line" />
              <ChartPanel title="Weekly aggregate minutes" data={minutes.weekly} />
              <ChartPanel title="Monthly aggregate minutes" data={minutes.monthly} />
            </div>
            <Heatmap values={minutes.heatmap.slice(-140)} />
          </>
        ) : (
          <div className="rounded-lg bg-white/[0.03] p-5 text-sm text-mist">No minute analytics available yet.</div>
        )}
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <ChartPanel title={`Listening by release decade - ${activeLabel}`} data={activeCharts.release_decades} />
        <ChartPanel title={`Dominant genre families - ${activeLabel}`} data={activeCharts.top_genre_clusters} type="pie" />
        <ChartPanel title={`Top artists by plays - ${activeLabel}`} data={activeCharts.top_artists} />
        <ChartPanel title={`Most repeated songs - ${activeLabel}`} data={activeCharts.most_repeated_songs} />
        <ChartPanel title={`Artist concentration - ${activeLabel}`} data={activeCharts.artist_concentration} type="pie" />
        <ChartPanel title={`Playlist influence - ${activeLabel}`} data={activeCharts.playlist_influence} />
        <div className="xl:col-span-2">
          <ChartPanel title={`Listening history timeline - ${activeLabel}`} data={activeCharts.coverage_timeline} type="line" />
        </div>
      </section>
    </div>
  );
}

function Heatmap({ values }: { values: ListeningMinutes["heatmap"] }) {
  if (!values.length) return null;
  const max = Math.max(...values.map((item) => item.value), 1);
  return (
    <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-white">Recent daily intensity</h3>
        <p className="text-xs text-mist">Darker cells mean more listening time.</p>
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
    </div>
  );
}

function periodLabel(period: PeriodValue) {
  return standardPeriodOptions.find((option) => option.value === period)?.label ?? "Selected Period";
}
