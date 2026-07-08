import { RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { TasteDNA } from "../components/TasteDNA";
import { CurrentListeningStateSection } from "../components/home/CurrentListeningStateSection";
import { ExploreProfileSection } from "../components/home/ExploreProfileSection";
import { KeySignalsStrip } from "../components/home/KeySignalsStrip";
import { MusicCharacterSection } from "../components/home/MusicCharacterSection";
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
  const nicheScore = scoreByKey.get("mainstream_niche");

  return (
    <div className="space-y-14">
      <TasteDNA dna={overview.taste_dna} interpretation={taste} />

      <MusicCharacterSection prerequisites={prerequisites} />

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
