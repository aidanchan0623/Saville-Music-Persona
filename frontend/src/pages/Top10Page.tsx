import { ArrowDown, ArrowUp, Minus, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import type { PeriodTopItem, PeriodTopResponse } from "../types/api";
import { formatDate } from "../utils/format";

type TopPeriod = "this_month" | "month" | "rolling_year";

export function Top10Page() {
  const [period, setPeriod] = useState<TopPeriod>("this_month");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [tracks, setTracks] = useState<PeriodTopResponse | null>(null);
  const [artists, setArtists] = useState<PeriodTopResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      api.periodTop(period, "tracks", period === "month" ? selectedMonth : null),
      api.periodTop(period, "artists", period === "month" ? selectedMonth : null),
    ])
      .then(([nextTracks, nextArtists]) => {
        if (cancelled) return;
        setTracks(nextTracks);
        setArtists(nextArtists);
        if (!selectedMonth && nextTracks.period.available_months.length) {
          setSelectedMonth(nextTracks.period.available_months[nextTracks.period.available_months.length - 1].value);
        }
      })
      .catch((nextError: Error) => {
        if (!cancelled) setError(nextError.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth]);

  const months = tracks?.period.available_months ?? artists?.period.available_months ?? [];
  const activeLabel = displayPeriodLabel(tracks?.period.label, period);

  if (!tracks && !artists && !loading) {
    return <EmptyState title="No rankings yet" body="Refresh your music data to build period rankings from detected plays." />;
  }

  return (
    <div className="space-y-7">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Top 10</h1>
          <p className="mt-2 max-w-3xl text-mist">
            Monthly and rolling-year rankings use deterministic play counts. Detected listening minutes are estimated from full track durations and always show coverage.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-panel/80 p-2">
          <PeriodButton active={period === "this_month"} label="This Month" onClick={() => setPeriod("this_month")} />
          <PeriodButton active={period === "month"} label="Select Month" onClick={() => setPeriod("month")} />
          <PeriodButton active={period === "rolling_year"} label="Rolling Year" onClick={() => setPeriod("rolling_year")} />
          {period === "month" ? (
            <select
              className="rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-white"
              value={selectedMonth ?? months.at(-1)?.value ?? ""}
              onChange={(event) => setSelectedMonth(event.target.value)}
            >
              {months.map((month) => (
                <option key={month.value} value={month.value}>{month.label}</option>
              ))}
            </select>
          ) : null}
        </div>
      </div>

      <section className="rounded-lg border border-violet/20 bg-panel/82 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.16em] text-violet-200">Analysing</p>
            <h2 className="mt-1 text-2xl font-black text-white">{activeLabel}</h2>
            <p className="mt-1 text-sm text-mist">
              {tracks?.period.start_date} to {tracks?.period.end_date}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-mist">
            <span className="rounded-full bg-white/10 px-3 py-1">{tracks?.total_play_count ?? 0} detected plays</span>
            <span className="rounded-full bg-white/10 px-3 py-1">{tracks?.ranked_music_play_count ?? 0} ranked music plays</span>
            <span className="rounded-full bg-white/10 px-3 py-1">{tracks?.duration_quality.duration_coverage_percent ?? 0}% duration coverage</span>
            <span className="rounded-full bg-white/10 px-3 py-1">{tracks?.duration_quality.confidence_badge}</span>
          </div>
        </div>
        {tracks?.sample_warning ? <p className="mt-4 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">{tracks.sample_warning}</p> : null}
        {error ? <p className="mt-4 rounded-md border border-red-300/10 bg-red-400/10 p-3 text-sm text-red-100">{error}</p> : null}
      </section>

      <section className="grid gap-7 xl:grid-cols-2">
        <TopList title={`Top Songs — ${displayPeriodLabel(tracks?.period.label, period)}`} response={tracks} loading={loading} />
        <TopList title={`Top Artists — ${displayPeriodLabel(artists?.period.label, period)}`} response={artists} loading={loading} artistList />
      </section>
    </div>
  );
}

function PeriodButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className={`rounded-md px-3 py-2 text-sm font-semibold transition ${active ? "bg-violet text-white" : "text-mist hover:bg-white/10 hover:text-white"}`} onClick={onClick}>
      {label}
    </button>
  );
}

function TopList({ title, response, loading, artistList = false }: { title: string; response: PeriodTopResponse | null; loading: boolean; artistList?: boolean }) {
  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-2xl font-bold text-white">{title}</h2>
        {loading ? <span className="text-sm text-mist">Loading...</span> : null}
      </div>
      <div className="space-y-3">
        {response?.items.length ? (
          response.items.map((item) => <PeriodTopCard key={item.key} item={item} artistList={artistList} />)
        ) : (
          <div className="rounded-lg border border-line bg-panel/80 p-5 text-sm text-mist">No detected plays in this period.</div>
        )}
      </div>
    </div>
  );
}

function PeriodTopCard({ item, artistList }: { item: PeriodTopItem; artistList: boolean }) {
  return (
    <article className="rounded-lg border border-line bg-panel/80 p-4 transition hover:border-violet/40">
      <div className="grid gap-4 sm:grid-cols-[2.6rem_1fr_auto]">
        <div className="text-2xl font-black text-white/30">#{item.rank}</div>
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold text-white">{artistList ? item.artist : item.title}</h3>
          <p className="mt-1 truncate text-sm text-violet-100">
            {artistList ? `${item.unique_songs ?? 0} unique songs${item.most_played_song ? ` - top: ${item.most_played_song}` : ""}` : item.artist}
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-mist">
            <span className="rounded-full bg-white/10 px-3 py-1">{item.play_count} plays</span>
            <span className="rounded-full bg-white/10 px-3 py-1">{item.detected_minutes_formatted}</span>
            <span className="rounded-full bg-white/10 px-3 py-1">{item.share_of_period}% share</span>
            <span className="rounded-full bg-white/10 px-3 py-1">{item.duration_coverage_percent}% duration coverage</span>
            {item.last_played ? <span className="rounded-full bg-white/10 px-3 py-1">Last {formatDate(item.last_played)}</span> : null}
          </div>
        </div>
        <div className="flex flex-row items-center gap-2 sm:flex-col sm:items-end">
          <span className="rounded-full border border-violet/30 bg-violet/10 px-3 py-1 text-xs font-semibold text-violet-100">{item.interpretation_label}</span>
          <Movement movement={item.movement} />
        </div>
      </div>
    </article>
  );
}

function Movement({ movement }: { movement: PeriodTopItem["movement"] }) {
  if (!movement) return null;
  const Icon = movement.direction === "up" ? ArrowUp : movement.direction === "down" ? ArrowDown : movement.direction === "new" ? Sparkles : Minus;
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 text-xs text-mist">
      <Icon size={13} /> {movement.label}
    </span>
  );
}

function displayPeriodLabel(label: string | undefined, period: TopPeriod) {
  if (period === "rolling_year") return "Rolling Year";
  return label ?? "Selected period";
}
