import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { TasteDNA } from "../components/TasteDNA";
import { CurrentListeningStateSection } from "../components/home/CurrentListeningStateSection";
import { ExploreProfileSection } from "../components/home/ExploreProfileSection";
import { HeroIdentitySection } from "../components/home/HeroIdentitySection";
import { KeySignalsStrip } from "../components/home/KeySignalsStrip";
import { TasteNarrativeSection } from "../components/home/TasteNarrativeSection";
import type {
  AuthStatus,
  ListeningMinutes,
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
}: Props) {
  const [currentTaste, setCurrentTaste] = useState<TasteDnaExplorer | null>(null);
  const [comparison, setComparison] = useState<TasteDnaComparison | null>(null);
  const [currentTopArtist, setCurrentTopArtist] = useState<PeriodTopItem | null>(null);

  useEffect(() => {
    if (!overview) return;
    let cancelled = false;
    Promise.allSettled([
      api.tasteDna("this_month"),
      api.tasteDnaCompare("rolling_year", "this_month"),
      api.periodTop("this_month", "artists"),
    ] as const).then(([tasteResult, comparisonResult, artistsResult]) => {
      if (cancelled) return;
      if (tasteResult.status === "fulfilled") setCurrentTaste(tasteResult.value);
      if (comparisonResult.status === "fulfilled") setComparison(comparisonResult.value);
      if (artistsResult.status === "fulfilled") setCurrentTopArtist(artistsResult.value.items[0] ?? null);
    });
    return () => {
      cancelled = true;
    };
  }, [overview?.last_refreshed_at]);

  const scoreByKey = useMemo(() => new Map(scores.map((score) => [score.key, score])), [scores]);

  if (!overview) {
    return (
      <EmptyState
        title="No listening analysis loaded yet"
        body="Connect YouTube Music for private local analysis, or switch on demo data to explore the dashboard without account access."
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
  const identityTitle = overview.taste_dna?.core_dna?.length
    ? overview.taste_dna.core_dna.slice(0, 3).join(" / ")
    : taste.core_genre_families.slice(0, 3).map((item) => item.name).join(" / ") || overview.headline_persona;
  const nicheScore = scoreByKey.get("mainstream_niche");
  const currentState = buildCurrentState(overview.repeat_score, overview.discovery_score, currentTopArtist?.artist);
  const connectedLabel = useDemo ? "Demo data active" : auth?.connected ? "YouTube Music connected" : "YouTube Music not connected";
  const modelLabel = prerequisites?.model_installed ? "Gemma ready" : "Gemma unavailable";

  return (
    <div className="space-y-14">
      <HeroIdentitySection
        identityTitle={identityTitle}
        summary={buildHeroSummary(taste)}
        currentState={currentState}
        connectedLabel={connectedLabel}
        modelLabel={modelLabel}
        lastRefreshedAt={overview.last_refreshed_at}
        busy={busy}
        onExploreTaste={onOpenScores}
        onViewThisMonth={onOpenTop10}
        onRefresh={onRefresh}
      />

      <KeySignalsStrip
        repeatScore={overview.repeat_score}
        discoveryScore={overview.discovery_score}
        nicheScore={nicheScore}
        thisMonthMinutes={thisMonthMinutes}
        rollingYearMinutes={rollingYearMinutes}
      />

      <TasteNarrativeSection taste={taste} />

      <TasteDNA dna={overview.taste_dna} interpretation={taste} />

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

function buildCurrentState(
  repeatScore: ScoreMetric,
  discoveryScore: ScoreMetric,
  currentArtist: string | undefined,
) {
  const replayPhrase = repeatScore.value >= 70
    ? "replay-heavy"
    : repeatScore.value >= 45
      ? "comfort-leaning"
      : "variety-led";
  const discoveryPhrase = discoveryScore.value >= 55 ? "actively exploratory" : "selectively curious";
  const anchor = currentArtist ? `, with ${currentArtist} as a current anchor` : "";
  return `This month you are ${replayPhrase} and ${discoveryPhrase}, still anchored by emotionally charged alternative music${anchor}.`;
}

function buildHeroSummary(taste: Overview["taste_interpretation"]) {
  const core = taste.core_genre_families.slice(0, 3).map((item) => item.name);
  const secondary = taste.secondary_genre_families.slice(0, 2).map((item) => item.name);
  const traits = taste.sonic_traits.slice(0, 4);
  const coreSentence = core.length
    ? `Your listening centres on ${formatInlineList(core)}.`
    : taste.summary;
  const traitSentence = traits.length
    ? `The strongest pattern feels ${formatInlineList(traits)}, with side colour from ${formatInlineList(secondary.length ? secondary : ["atmospheric and nostalgic listening"])}.`
    : "The strongest pattern is emotionally charged, guitar-driven, and atmospheric.";
  return `${coreSentence} ${traitSentence}`;
}

function formatInlineList(items: string[]) {
  if (items.length <= 1) return items[0] ?? "";
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}
