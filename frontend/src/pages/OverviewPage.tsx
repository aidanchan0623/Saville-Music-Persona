import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { GlowPanel } from "../components/GlowPanel";
import { PageTitlePanel } from "../components/PageTitlePanel";
import { TasteDNA } from "../components/TasteDNA";
import { CurrentListeningStateSection } from "../components/home/CurrentListeningStateSection";
import { ExploreProfileSection } from "../components/home/ExploreProfileSection";
import { KeySignalsStrip } from "../components/home/KeySignalsStrip";
import { MusicCharacterSection } from "../components/home/MusicCharacterSection";
import { TasteNarrativeSection } from "../components/home/TasteNarrativeSection";
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
  titleAnimationKey: string;
}

export function OverviewPage({
  overview,
  thisMonthMinutes,
  rollingYearMinutes,
  scores,
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
  titleAnimationKey,
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
  }, [overview?.last_refreshed_at, source]);

  const scoreByKey = useMemo(() => new Map(scores.map((score) => [score.key, score])), [scores]);

  if (!overview) {
    return (
      <EmptyState
        title="No listening analysis loaded yet"
        body={source === "spotify" ? "Connect Spotify to generate a music profile from your Spotify top artists, top tracks, saved songs, playlists and recent plays." : "Connect YouTube Music for private local analysis, or switch on demo data to explore the dashboard without account access."}
        titleTag="h1"
        titleAnimationKey={titleAnimationKey}
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
  const sourceLabel = source === "spotify" ? "Spotify" : "YouTube Music";
  const coreTitle = overview.headline_persona || taste.core_genre_families.map((cluster) => cluster.name).slice(0, 2).join(" / ") || "Music identity";
  const summary = taste.summary || "A compact read of your current listening profile from local music data.";
  const topTracks = overview.top_3_tracks.slice(0, 3);
  const topArtists = overview.top_3_artists.slice(0, 3);

  return (
    <div className="space-y-8">
      <PageTitlePanel
        eyebrow="Private local music identity"
        title={coreTitle}
        titleAnimationKey={titleAnimationKey}
        titleClassName="max-w-4xl text-3xl font-black leading-tight text-white md:text-4xl"
        subtitle={summary}
        subtitleClassName="mt-4 line-clamp-3 max-w-3xl text-base leading-7 text-mist"
        lineMode="animated"
        actions={
          <GlowPanel as="div" variant="row" className="p-4">
            <p className="text-sm font-semibold text-red-100">Most active sound</p>
            <p className="mt-2 text-2xl font-black leading-tight text-white">{overview.top_genre_cluster || "Still mapping"}</p>
            <button className="btn-primary mt-5 w-full" type="button" onClick={onOpenReport}>
              Open Persona Report
            </button>
          </GlowPanel>
        }
        metadata={
          <>
            <span className="rounded-md border border-line bg-white/[0.04] px-3 py-1.5">Source: {sourceLabel}</span>
            <span className="rounded-md border border-line bg-white/[0.04] px-3 py-1.5">{overview.coverage.days_represented.toLocaleString()} days represented</span>
            <span className="rounded-md border border-line bg-white/[0.04] px-3 py-1.5">Updated: {overview.last_refreshed_at ? formatShortDate(overview.last_refreshed_at) : "Not refreshed yet"}</span>
          </>
        }
      />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryMetric label="Detected plays" value={overview.total_detected_plays.toLocaleString()} detail={overview.coverage.history_coverage_status} />
        <SummaryMetric label="Unique tracks" value={overview.unique_tracks.toLocaleString()} detail="Songs in the local profile" />
        <SummaryMetric label="Unique artists" value={overview.unique_artists.toLocaleString()} detail="Artists detected in history" />
        <SummaryMetric label="Genre coverage" value={`${Math.round(overview.genre_coverage_percent)}%`} detail="Mapped listening coverage" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <GlowPanel as="div" variant="card" className="p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">Listening overview</p>
          <h2 className="mt-2 text-2xl font-black text-white">Recent scale</h2>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <SummaryMetric label="This month" value={thisMonthMinutes?.metrics.selected_period_total_formatted ?? "Unavailable"} detail={thisMonthMinutes?.summary_sentence ?? "Minute analysis appears after duration enrichment."} compact />
            <SummaryMetric label="Rolling year" value={rollingYearMinutes?.metrics.selected_period_total_formatted ?? "Unavailable"} detail={rollingYearMinutes?.summary_sentence ?? "Detected minutes are limited by duration coverage."} compact />
          </div>
        </GlowPanel>
        <div className="grid gap-4 lg:grid-cols-2">
          <PreviewList title="Top songs preview" empty="No top songs available yet." items={topTracks.map((track) => ({ key: track.track_id || `${track.rank}-${track.title}`, rank: track.rank, title: track.title, subtitle: track.artist, metric: `${track.play_count.toLocaleString()} plays` }))} />
          <PreviewList title="Top artists preview" empty="No top artists available yet." items={topArtists.map((artist) => ({ key: artist.artist_id || `${artist.rank}-${artist.artist}`, rank: artist.rank, title: artist.artist, subtitle: artist.most_played_song ? `Top song: ${artist.most_played_song}` : `${artist.unique_songs_played} songs`, metric: `${artist.play_count.toLocaleString()} plays` }))} />
        </div>
      </section>

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

function SummaryMetric({ label, value, detail, compact = false }: { label: string; value: string; detail: string; compact?: boolean }) {
  return (
    <GlowPanel as="article" variant="card" className={compact ? "p-4" : "p-5"}>
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/65">{label}</p>
      <p className={`${compact ? "mt-2 text-2xl" : "mt-3 text-3xl"} font-black leading-tight text-white`}>{value}</p>
      <p className="mt-2 line-clamp-2 text-xs leading-5 text-mist">{detail}</p>
    </GlowPanel>
  );
}

function PreviewList({
  title,
  items,
  empty,
}: {
  title: string;
  empty: string;
  items: { key: string; rank: number; title: string; subtitle: string; metric: string }[];
}) {
  return (
    <GlowPanel as="section" variant="card" className="p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-black text-white">{title}</h2>
        <span className="text-xs text-mist">{items.length} shown</span>
      </div>
      <div className="mt-4 space-y-2">
        {items.length ? items.map((item) => (
          <GlowPanel key={item.key} as="article" variant="row" className="grid grid-cols-[2.5rem_1fr_auto] items-center gap-3 p-3">
            <span className="text-lg font-black text-red-200">#{item.rank}</span>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-white">{item.title}</p>
              <p className="truncate text-xs text-mist">{item.subtitle}</p>
            </div>
            <span className="whitespace-nowrap text-xs font-semibold text-mist">{item.metric}</span>
          </GlowPanel>
        )) : <GlowPanel as="p" variant="row" className="p-3 text-sm text-mist">{empty}</GlowPanel>}
      </div>
    </GlowPanel>
  );
}

function formatShortDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
