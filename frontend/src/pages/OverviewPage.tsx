import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { PageTitlePanel } from "../components/PageTitlePanel";
import { OverviewStepper } from "../components/home/OverviewStepper";
import type {
  AuthStatus,
  ListeningMinutes,
  MusicSource,
  Overview,
  PeriodTopResponse,
  Prerequisites,
  ScoreMetric,
  TasteDnaComparison,
  TasteDnaExplorer,
} from "../types/api";
import { resolvePersonaVisualTheme } from "../utils/personaVisualTheme";

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
  const [currentTopArtists, setCurrentTopArtists] = useState<PeriodTopResponse | null>(null);
  const [currentTopTracks, setCurrentTopTracks] = useState<PeriodTopResponse | null>(null);

  useEffect(() => {
    if (!overview) {
      setCurrentTaste(null);
      setComparison(null);
      setCurrentTopArtists(null);
      setCurrentTopTracks(null);
      return;
    }
    let cancelled = false;
    setCurrentTaste(null);
    setComparison(null);
    setCurrentTopArtists(null);
    setCurrentTopTracks(null);
    api.tasteDna("this_month", null, source)
      .then((value) => {
        if (!cancelled) setCurrentTaste(value);
      })
      .catch(() => {
        if (!cancelled) setCurrentTaste(null);
      });
    api.tasteDnaCompare("rolling_year", "this_month", null, source)
      .then((value) => {
        if (!cancelled) setComparison(value);
      })
      .catch(() => {
        if (!cancelled) setComparison(null);
      });
    api.periodTop("this_month", "artists", null, source)
      .then((value) => {
        if (!cancelled) setCurrentTopArtists(value);
      })
      .catch(() => {
        if (!cancelled) setCurrentTopArtists(null);
      });
    api.periodTop("this_month", "tracks", null, source)
      .then((value) => {
        if (!cancelled) setCurrentTopTracks(value);
      })
      .catch(() => {
        if (!cancelled) setCurrentTopTracks(null);
      });
    return () => {
      cancelled = true;
    };
  }, [overview?.last_refreshed_at, source]);

  if (!overview) {
    return (
      <div className="space-y-6">
      <PageTitlePanel
        eyebrow="Private local music identity"
        title="No listening analysis loaded yet"
        titleAnimationKey={titleAnimationKey}
        subtitle={source === "spotify" ? "Connect Spotify to generate a music profile from your Spotify top artists, top tracks, saved songs, playlists and recent plays." : "Connect YouTube Music for private local analysis, or switch on demo data to explore the dashboard without account access."}
        actions={
          <div className="flex flex-wrap justify-center gap-3">
            <button className="btn-primary" onClick={onRefresh} disabled={busy}>
              <RefreshCw size={17} /> {busy ? "Refreshing..." : useDemo ? "Load Demo Data" : "Refresh My Music Data"}
            </button>
            <button className="btn-secondary" onClick={onOpenSettings}>Open Settings</button>
          </div>
        }
      />
      </div>
    );
  }

  const taste = overview.taste_interpretation;
  const sourceLabel = source === "spotify" ? "Spotify" : "YouTube Music";
  const coreTitle = overview.headline_persona || taste.core_genre_families.map((cluster) => cluster.name).slice(0, 2).join(" / ") || "Music identity";
  const summary = taste.summary || "A compact read of your current listening profile from local music data.";
  const visualTheme = resolvePersonaVisualTheme(overview, currentTaste);
  const updatedLabel = overview.last_refreshed_at ? formatShortDate(overview.last_refreshed_at) : "not refreshed yet";

  return (
    <div className="space-y-7">
      <PageTitlePanel
        eyebrow="Private local music identity"
        title={coreTitle}
        titleAnimationKey={titleAnimationKey}
        titleClassName="max-w-4xl text-3xl font-black leading-tight text-white md:text-4xl"
        subtitle={summary}
        subtitleClassName="mt-4 max-w-3xl text-base leading-7 text-mist"
        lineMode="animated"
        className="overview-hero-panel"
        backgroundImage={visualTheme.primaryImage.src}
        backgroundPosition={visualTheme.primaryImage.position ?? visualTheme.position}
        overlayStrength={visualTheme.overlayStrength}
        actions={
          <div className="overview-hero-sound">
            <p className="overview-hero-sound__label">Most active sound</p>
            <p className="overview-hero-sound__value">{overview.top_genre_cluster || "Still mapping"}</p>
            <p className="overview-hero-sound__context">{visualTheme.accentLabel}</p>
            <button className="btn-primary mt-5" type="button" onClick={onOpenReport}>
              Open Persona Report
            </button>
          </div>
        }
        metadata={
          <span>{sourceLabel} &middot; {overview.coverage.days_represented.toLocaleString()} days analysed &middot; Updated {updatedLabel}</span>
        }
      />

      <OverviewStepper
        overview={overview}
        thisMonthMinutes={thisMonthMinutes}
        rollingYearMinutes={rollingYearMinutes}
        scores={scores}
        currentTaste={currentTaste}
        comparison={comparison}
        currentTopArtists={currentTopArtists}
        currentTopTracks={currentTopTracks}
        visualTheme={visualTheme}
        onOpenTop10={onOpenTop10}
        onOpenScores={onOpenScores}
        onOpenPatterns={onOpenPatterns}
        onOpenReport={onOpenReport}
      />
    </div>
  );
}

function formatShortDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
