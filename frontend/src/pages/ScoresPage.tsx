import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { getScoreKind, getScorePresentation, ScoreGauge, type ScoreKind } from "../components/ScoreGauge";
import { MetricBlock } from "../components/ui/MetricBlock";
import { PageHeader } from "../components/ui/PageHeader";
import { PeriodSelector, type PeriodValue, standardPeriodOptions } from "../components/ui/PeriodSelector";
import type { ListeningMinutes, MusicSource, ScoreMetric } from "../types/api";
import { asPercent, formatMinutes } from "../utils/format";

export function ScoresPage({ scores: initialScores, source }: { scores: ScoreMetric[]; source: MusicSource }) {
  const [period, setPeriod] = useState<PeriodValue>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [scores, setScores] = useState<ScoreMetric[]>(initialScores);
  const [minutes, setMinutes] = useState<ListeningMinutes | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => setScores(initialScores), [initialScores]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      api.scoreInterpretations(period, period === "month" ? selectedMonth : null, source),
      api.listeningMinutes(period, period === "month" ? selectedMonth : null, source),
    ])
      .then(([nextScores, nextMinutes]) => {
        if (cancelled) return;
        setScores(nextScores);
        setMinutes(nextMinutes);
        if (!selectedMonth && nextMinutes.period.available_months.length) {
          setSelectedMonth(nextMinutes.period.available_months[nextMinutes.period.available_months.length - 1].value);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth, source]);

  if (!scores.length) return <EmptyState title="No scorecard yet" body="Refresh data to calculate deterministic scores with transparent formulas." />;

  const groups = buildScoreGroups(scores);
  const glanceScores = getAtAGlanceScores(scores);
  const months = minutes?.period.available_months ?? [];
  const periodLabel = displayPeriodLabel(minutes?.period.label, period);
  const playCount = minutes?.duration_quality.total_detected_plays ?? 0;
  const limitedSample = period !== "rolling_year" && period !== "all" && playCount < 50;
  const topScore = glanceScores[0];

  return (
    <div className="space-y-9">
      <section className="editorial-panel overflow-hidden">
        <div className="p-5 md:p-8">
          <PageHeader
            eyebrow="Music listening profile"
            title="Taste Scores"
            description={
              source === "spotify"
                ? "Spotify scores translate top-item, saved-library, playlist, and recent-sync signals into the same local music-profile framework."
                : "These scores translate the selected period into replay, discovery, artist pull, and the shape of your sound world."
            }
            action={<PeriodSelector value={period} onChange={setPeriod} month={selectedMonth} months={months} onMonthChange={setSelectedMonth} options={standardPeriodOptions} />}
            meta={
              <>
                <span className="subtle-pill border-red-400/20 bg-red-500/10 text-red-100">{periodLabel}</span>
                {loading ? <span className="subtle-pill">Updating</span> : null}
                {source === "spotify" ? <span className="subtle-pill">Spotify top-item based</span> : null}
                {limitedSample ? <span className="subtle-pill border-amber-200/20 bg-amber-200/10 text-amber-100">Limited sample</span> : null}
              </>
            }
          />
        </div>
        <div className="grid gap-px border-t border-white/10 bg-white/10 md:grid-cols-3">
          <MetricBlock label="Detected plays" value={playCount.toLocaleString()} caption="Signals used for this period" index={1} />
          <MetricBlock label="Detected minutes" value={minutes ? formatMinutes(minutes.metrics.selected_period_total_minutes) : "Unavailable"} caption={minutes?.duration_quality.confidence_badge ?? "Waiting for duration coverage"} index={2} />
          <MetricBlock label="Loudest trait" value={topScore ? getScorePresentation(topScore).tag : "Still forming"} caption={topScore ? asPercent(topScore.value) : "No score yet"} index={3} />
        </div>
      </section>

      <section className="editorial-panel p-5 md:p-7">
        <div className="mb-5 flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="section-label">At a glance</p>
            <h2 className="mt-2 text-3xl font-black text-white">Score identity strip</h2>
          </div>
          <p className="max-w-2xl text-sm leading-6 text-mist">Short labels summarize the calculated scores; open cards below keep the evidence and formula visible.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          {glanceScores.map((score) => {
            const presentation = getScorePresentation(score);
            return (
              <div key={score.key} className="rounded-full border border-white/10 bg-white/[0.055] px-4 py-2.5 shadow-[0_10px_40px_rgba(0,0,0,0.16)]">
                <span className="text-sm font-semibold text-white">{presentation.tag}</span>
                <span className="ml-2 text-sm text-red-200">{asPercent(score.value)}</span>
              </div>
            );
          })}
        </div>
      </section>

      <div className="space-y-9">
        {groups.map((group) => <ScoreSection key={group.title} title={group.title} description={group.description} scores={group.scores} />)}
      </div>
    </div>
  );
}

function displayPeriodLabel(label: string | undefined, period: PeriodValue) {
  if (period === "rolling_year") return "Rolling Year";
  return label ?? standardPeriodOptions.find((option) => option.value === period)?.label ?? "Selected Period";
}

function ScoreSection({ title, description, scores }: { title: string; description: string; scores: ScoreMetric[] }) {
  if (!scores.length) return null;
  return (
    <section className="editorial-panel p-5 md:p-7">
      <div className="mb-6 max-w-3xl">
        <p className="section-label">{title}</p>
        <h2 className="mt-2 text-3xl font-black text-white">{title}</h2>
        <p className="mt-2 text-base leading-7 text-mist">{description}</p>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {scores.map((score) => {
          const kind = getScoreKind(score);
          return <ScoreGauge key={score.key} score={score} featured={kind === "repeat" || kind === "broadCluster"} />;
        })}
      </div>
    </section>
  );
}

function buildScoreGroups(scores: ScoreMetric[]) {
  const used = new Set<string>();
  const take = (kinds: ScoreKind[]) => {
    const groupScores: ScoreMetric[] = [];
    for (const kind of kinds) {
      const score = scores.find((item) => getScoreKind(item) === kind && !used.has(item.key));
      if (score) {
        groupScores.push(score);
        used.add(score.key);
      }
    }
    return groupScores;
  };

  const listeningHabits = take(["repeat", "discovery", "artistLoyalty"]);
  const tasteShape = take(["broadCluster", "withinCluster", "nostalgia"]);
  const positioning = take(["mainstreamNiche", "tasteConfidence"]);
  const remaining = scores.filter((score) => !used.has(score.key));

  return [
    {
      title: "Listening Habits",
      description: "How you move through music: replay, discovery, and artist attachment.",
      scores: listeningHabits,
    },
    {
      title: "Taste Shape",
      description: "How broad, focused, current-facing, or internally varied your musical world is.",
      scores: tasteShape,
    },
    {
      title: "Positioning",
      description: "How your listening sits relative to mainstream popularity and available metadata.",
      scores: [...positioning, ...remaining],
    },
  ].filter((group) => group.scores.length);
}

function getAtAGlanceScores(scores: ScoreMetric[]) {
  const priority: ScoreKind[] = ["repeat", "discovery", "artistLoyalty", "broadCluster", "mainstreamNiche"];
  const picked: ScoreMetric[] = [];
  const seen = new Set<string>();
  for (const kind of priority) {
    const score = scores.find((item) => getScoreKind(item) === kind && !seen.has(item.key));
    if (score) {
      picked.push(score);
      seen.add(score.key);
    }
  }
  for (const score of scores) {
    if (picked.length >= 5) break;
    if (!seen.has(score.key)) {
      picked.push(score);
      seen.add(score.key);
    }
  }
  return picked.slice(0, 5);
}
