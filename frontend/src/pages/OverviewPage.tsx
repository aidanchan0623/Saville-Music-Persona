import { ArrowRight, Database, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { LineWaves } from "../components/LineWaves";
import { TasteDNA } from "../components/TasteDNA";
import { CurrentListeningStateSection } from "../components/home/CurrentListeningStateSection";
import { ExploreProfileSection } from "../components/home/ExploreProfileSection";
import { KeySignalsStrip } from "../components/home/KeySignalsStrip";
import { MusicCharacterSection } from "../components/home/MusicCharacterSection";
import { TasteNarrativeSection } from "../components/home/TasteNarrativeSection";
import { Artwork } from "../components/ui/Artwork";
import { MetricBlock } from "../components/ui/MetricBlock";
import type {
  AuthStatus,
  ListeningMinutes,
  MusicSource,
  Overview,
  PeriodTopItem,
  Prerequisites,
  ScoreMetric,
  TasteDnaComparison,
  TasteDnaExplorer,
} from "../types/api";
import { formatDateTime, formatMinutes } from "../utils/format";

interface Props {
  overview: Overview | null;
  thisMonthMinutes: ListeningMinutes | null;
  rollingYearMinutes: ListeningMinutes | null;
  scores: ScoreMetric[];
  auth: AuthStatus | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  useDemo: boolean;
  onRefresh: () => void;
  onOpenSettings: () => void;
  onOpenTop10: () => void;
  onOpenScores: () => void;
  onOpenPatterns: () => void;
  onOpenReport: () => void;
  source: MusicSource;
}

export function OverviewPage({
  overview,
  thisMonthMinutes,
  rollingYearMinutes,
  scores,
  auth,
  prerequisites,
  busy,
  useDemo,
  onRefresh,
  onOpenSettings,
  onOpenTop10,
  onOpenScores,
  onOpenPatterns,
  onOpenReport,
  source,
}: Props) {
  const [currentTaste, setCurrentTaste] = useState<TasteDnaExplorer | null>(null);
  const [comparison, setComparison] = useState<TasteDnaComparison | null>(null);
  const [currentTopArtist, setCurrentTopArtist] = useState<PeriodTopItem | null>(null);

  useEffect(() => {
    if (!overview) return;
    let cancelled = false;
    Promise.allSettled([
      api.tasteDna("this_month", null, source),
      api.tasteDnaCompare("rolling_year", "this_month", null, source),
      api.periodTop("this_month", "artists", null, source),
    ] as const).then(([tasteResult, comparisonResult, artistsResult]) => {
      if (cancelled) return;
      if (tasteResult.status === "fulfilled") setCurrentTaste(tasteResult.value);
      if (comparisonResult.status === "fulfilled") setComparison(comparisonResult.value);
      if (artistsResult.status === "fulfilled") setCurrentTopArtist(artistsResult.value.items[0] ?? null);
    });
    return () => {
      cancelled = true;
    };
  }, [overview, source]);

  const scoreByKey = useMemo(() => new Map(scores.map((score) => [score.key, score])), [scores]);

  if (!overview) {
    return (
      <EmptyState
        title="No listening analysis loaded yet"
        body={source === "spotify" ? "Connect Spotify to generate a music profile from your Spotify top artists, top tracks, saved songs, playlists and recent plays." : "Connect YouTube Music for private local analysis, or switch on demo data to explore the dashboard without account access."}
        action={
          <div className="flex flex-wrap justify-center gap-3">
            <button className="btn-primary" onClick={onRefresh} disabled={busy}>
              <RefreshCw size={17} /> {busy ? "Refreshing..." : useDemo ? "Load Demo Data" : "Refresh My Music Data"}
            </button>
            <button className="btn-secondary" onClick={onOpenSettings}>Open Settings</button>
          </div>
        }
      />
    );
  }

  const taste = overview.taste_interpretation;
  const nicheScore = scoreByKey.get("mainstream_niche");

  return (
    <div className="space-y-14">
      <PersonaHero
        overview={overview}
        thisMonthMinutes={thisMonthMinutes}
        rollingYearMinutes={rollingYearMinutes}
        auth={auth}
        prerequisites={prerequisites}
        busy={busy}
        useDemo={useDemo}
        source={source}
        onRefresh={onRefresh}
        onOpenTop10={onOpenTop10}
        onOpenReport={onOpenReport}
      />

      <TasteDNA dna={overview.taste_dna} interpretation={taste} source={source} />

      <MusicCharacterSection prerequisites={prerequisites} source={source} />

      <KeySignalsStrip
        repeatScore={overview.repeat_score}
        discoveryScore={overview.discovery_score}
        nicheScore={nicheScore}
        thisMonthMinutes={thisMonthMinutes}
        rollingYearMinutes={rollingYearMinutes}
      />

      <TasteNarrativeSection taste={taste} />

      <CurrentListeningStateSection
        currentMinutes={thisMonthMinutes}
        currentTaste={currentTaste}
        comparison={comparison}
        currentTopArtist={currentTopArtist}
        repeatScore={overview.repeat_score}
        discoveryScore={overview.discovery_score}
      />

      <ExploreProfileSection
        onOpenTop10={onOpenTop10}
        onOpenScores={onOpenScores}
        onOpenPatterns={onOpenPatterns}
        onOpenReport={onOpenReport}
      />
    </div>
  );
}

function PersonaHero({
  overview,
  thisMonthMinutes,
  rollingYearMinutes,
  auth,
  prerequisites,
  busy,
  useDemo,
  source,
  onRefresh,
  onOpenTop10,
  onOpenReport,
}: {
  overview: Overview;
  thisMonthMinutes: ListeningMinutes | null;
  rollingYearMinutes: ListeningMinutes | null;
  auth: AuthStatus | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  useDemo: boolean;
  source: MusicSource;
  onRefresh: () => void;
  onOpenTop10: () => void;
  onOpenReport: () => void;
}) {
  const heroArt = [
    ...overview.top_3_tracks.map((track) => ({ label: track.title, byline: track.artist, image: track.thumbnail })),
    ...overview.top_3_artists.map((artist) => ({ label: artist.artist, byline: artist.why_it_matters || artist.artist_loyalty_label, image: artist.image })),
  ].slice(0, 5);
  const minutesLabel = rollingYearMinutes
    ? formatMinutes(rollingYearMinutes.metrics.rolling_365_total_minutes)
    : thisMonthMinutes
      ? formatMinutes(thisMonthMinutes.metrics.current_month_total_minutes)
      : "Unavailable";
  const sourceLabel = overview.source_label || (source === "spotify" ? "Spotify" : "YouTube Music");
  const connectionLabel = source === "youtube"
    ? useDemo
      ? "Demo mode"
      : auth?.connected
        ? "Live YouTube connected"
        : auth?.cached_data_available
          ? "Cached YouTube data"
          : "YouTube needs setup"
    : "Spotify source selected";
  const modelLabel = prerequisites?.ollama_reachable && prerequisites.model_installed ? "Gemma ready" : "Deterministic mode";

  return (
    <section className="relative isolate overflow-hidden rounded-lg border border-white/10 bg-[#090505] shadow-glow">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_16%_20%,rgba(239,68,68,0.28),transparent_33%),radial-gradient(circle_at_76%_0%,rgba(127,29,29,0.24),transparent_30%),linear-gradient(135deg,rgba(7,3,3,0.98),rgba(24,8,8,0.94)_52%,rgba(5,3,3,0.98))]" />
      <LineWaves className="opacity-70" amplitude={24} speed={0.00012} waveCount={6} />
      <div className="relative grid gap-8 p-5 md:p-8 xl:grid-cols-[minmax(0,1.06fr)_minmax(24rem,0.94fr)] xl:p-10">
        <div className="flex min-h-[34rem] flex-col justify-between">
          <div>
            <div className="flex flex-wrap gap-2">
              <span className="subtle-pill border-red-400/20 bg-red-500/10 text-red-100">{sourceLabel}</span>
              <span className="subtle-pill">{connectionLabel}</span>
              <span className="subtle-pill">{modelLabel}</span>
            </div>
            <p className="mt-8 section-label">Private local music identity</p>
            <h1 className="mt-4 max-w-5xl font-display text-5xl uppercase leading-[0.84] tracking-[0.03em] text-white md:text-7xl xl:text-8xl">
              Saville Music Persona
            </h1>
            <p className="mt-5 max-w-4xl text-2xl font-black leading-tight text-red-100 md:text-4xl">{overview.headline_persona}</p>
            <p className="mt-5 max-w-3xl text-base leading-8 text-mist md:text-lg">{overview.taste_interpretation.summary}</p>
          </div>

          <div className="mt-8">
            <div className="flex flex-wrap gap-3">
              <button className="btn-primary px-5 py-3" onClick={onOpenReport}>
                Read Persona Report <ArrowRight size={18} />
              </button>
              <button className="btn-secondary px-5 py-3" onClick={onOpenTop10}>
                View Top 10 <ArrowRight size={18} />
              </button>
              <button className="btn-secondary px-5 py-3" onClick={onRefresh} disabled={busy}>
                <RefreshCw size={17} className={busy ? "animate-spin" : ""} /> {busy ? "Refreshing" : "Refresh"}
              </button>
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-mist">
              <span>Last refreshed: {formatDateTime(overview.last_refreshed_at)}</span>
              <span className="hidden h-1 w-1 rounded-full bg-red-300/70 sm:inline-block" />
              <span>{overview.coverage.days_represented.toLocaleString()} days represented</span>
            </div>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-rows-[1fr_auto]">
          <div className="grid min-h-[24rem] grid-cols-6 grid-rows-6 gap-3">
            {heroArt[0] ? <Artwork className="col-span-4 row-span-4 h-full w-full" src={heroArt[0].image} alt={heroArt[0].label} /> : null}
            {heroArt[1] ? <Artwork className="col-span-2 row-span-3 h-full w-full" src={heroArt[1].image} alt={heroArt[1].label} rounded="circle" /> : null}
            {heroArt[2] ? <Artwork className="col-span-2 row-span-3 h-full w-full" src={heroArt[2].image} alt={heroArt[2].label} /> : null}
            {heroArt[3] ? <Artwork className="col-span-3 row-span-2 h-full w-full" src={heroArt[3].image} alt={heroArt[3].label} /> : null}
            {heroArt[4] ? <Artwork className="col-span-3 row-span-2 h-full w-full" src={heroArt[4].image} alt={heroArt[4].label} /> : null}
          </div>
          <div className="grid gap-px overflow-hidden rounded-lg border border-white/10 bg-white/10 sm:grid-cols-2">
            {overview.top_3_tracks.slice(0, 2).map((track) => (
              <article key={track.track_id} className="bg-black/30 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-mist/60">Top track #{track.rank}</p>
                <p className="mt-2 truncate text-base font-black text-white">{track.title}</p>
                <p className="truncate text-sm text-red-100/80">{track.artist}</p>
              </article>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-px border-t border-white/10 bg-white/10 md:grid-cols-2 xl:grid-cols-6">
        <MetricBlock label="Detected plays" value={overview.total_detected_plays.toLocaleString()} caption="Local merged history" index={1} />
        <MetricBlock label="Detected minutes" value={minutesLabel} caption="Duration-aware estimate" index={2} />
        <MetricBlock label="Unique tracks" value={overview.unique_tracks.toLocaleString()} caption={`${overview.unique_artists.toLocaleString()} artists`} index={3} />
        <MetricBlock label="Top sound" value={overview.top_genre_cluster || "Mapped profile"} caption={overview.favourite_decade} index={4} />
        <MetricBlock label="Taste confidence" value={`${Math.round(overview.taste_confidence.value)}%`} caption={overview.taste_confidence.label} index={5} />
        <MetricBlock label="Coverage" value={overview.coverage.full_365_day_analysis ? "Full year" : "Partial"} caption={`${overview.coverage.dated_history_items.toLocaleString()} dated events`} index={6} tone={overview.coverage.full_365_day_analysis ? "green" : "amber"} />
      </div>

      <div className="border-t border-white/10 p-5 md:p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <EvidenceLine icon={<Database size={17} />} title="Longest available data" text={overview.coverage.history_coverage_status || "Analysis uses the longest dated local cache available."} />
          <EvidenceLine icon={<ShieldCheck size={17} />} title="Local-first privacy" text="Credentials, Takeout files, cached reports, and playlist exports stay in the local repo/private data folders." />
        </div>
      </div>
    </section>
  );
}

function EvidenceLine({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="flex gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-4">
      <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-md bg-red-500/12 text-red-100">{icon}</span>
      <div>
        <p className="font-semibold text-white">{title}</p>
        <p className="mt-1 text-sm leading-6 text-mist">{text}</p>
      </div>
    </div>
  );
}
