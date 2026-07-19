import { useEffect, useState } from "react";
import { api } from "../api/client";
import { GlowPanel } from "../components/GlowPanel";
import { PageTitlePanel } from "../components/PageTitlePanel";
import { getScoreKind, getScorePresentation, ScoreGauge, type ScoreKind } from "../components/ScoreGauge";
import type { ListeningMinutes, MusicSource, ScoreMetric } from "../types/api";
import { asPercent } from "../utils/format";

type ScorePeriod = "this_month" | "month" | "rolling_year";

export function ScoresPage({ scores: initialScores, source, titleAnimationKey }: { scores: ScoreMetric[]; source: MusicSource; titleAnimationKey: string }) {
  const [period, setPeriod] = useState<ScorePeriod>("rolling_year");
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

  if (!scores.length) {
    return (
      <div className="space-y-6">
        <PageTitlePanel
          eyebrow="Music listening profile"
          title="Taste Scores"
          titleAnimationKey={titleAnimationKey}
          titleClassName="text-5xl font-black leading-[0.95] tracking-tight text-white md:text-7xl"
          subtitle="Refresh data to calculate deterministic scores with transparent formulas."
        />
        <GlowPanel as="section" variant="card" className="p-5 text-sm text-mist">No scorecard yet.</GlowPanel>
      </div>
    );
  }
  const groups = buildScoreGroups(scores);
  const glanceScores = getAtAGlanceScores(scores);
  const months = minutes?.period.available_months ?? [];
  const periodLabel = displayPeriodLabel(minutes?.period.label, period);
  const playCount = minutes?.duration_quality.total_detected_plays ?? 0;
  const limitedSample = period !== "rolling_year" && playCount < 50;

  return (
    <div className="space-y-12">
      <PageTitlePanel
        eyebrow="Music listening profile"
        title="Taste Scores"
        titleAnimationKey={titleAnimationKey}
        titleClassName="text-5xl font-black leading-[0.95] tracking-tight text-white md:text-7xl"
        subtitle={
          <>
            <p className="max-w-3xl text-2xl font-semibold leading-snug text-red-100">
              {periodLabel} read on how you listen - not just what you play.
            </p>
            <p className="mt-4 max-w-3xl text-base leading-8 text-mist md:text-lg">
            {source === "spotify"
              ? "Spotify scores translate top-item, saved-library, playlist, and recent-sync signals into the same music-profile framework."
              : "These scores translate the selected period into a music profile: replay, discovery, artist pull, and the shape of your sound world."}
            </p>
          </>
        }
        subtitleClassName="mt-5"
        actions={
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-panel/80 p-2">
          <PeriodButton active={period === "this_month"} label="This Month" onClick={() => setPeriod("this_month")} />
          <PeriodButton active={period === "month"} label="Select Month" onClick={() => setPeriod("month")} />
          <PeriodButton active={period === "rolling_year"} label="Rolling Year" onClick={() => setPeriod("rolling_year")} />
          {period === "month" ? (
            <select className="rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-white" value={selectedMonth ?? months.at(-1)?.value ?? ""} onChange={(event) => setSelectedMonth(event.target.value)}>
              {months.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
            </select>
          ) : null}
          </div>
        }
      />

      <GlowPanel as="section" variant="card" className="p-4 text-sm text-mist">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-white">Analysing {periodLabel}</span>
          {loading ? <span className="rounded-full bg-white/10 px-3 py-1 text-xs">Updating...</span> : null}
          {minutes ? <span className="rounded-full bg-white/10 px-3 py-1 text-xs">{playCount.toLocaleString()} detected plays</span> : null}
          {source === "spotify" ? <span className="rounded-full bg-white/10 px-3 py-1 text-xs">Spotify top-item based</span> : null}
          {limitedSample ? <span className="rounded-full bg-amber-200/10 px-3 py-1 text-xs text-amber-100">Limited sample for this month</span> : null}
        </div>
      </GlowPanel>

      <GlowPanel as="section" variant="card" lined className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center">
        <div className="lg:w-44">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-200">At a glance</p>
        </div>
        <div className="flex flex-1 flex-wrap gap-3">
          {glanceScores.map((score) => {
            const presentation = getScorePresentation(score);
            return (
              <div key={score.key} className="rounded-full border border-white/10 bg-white/[0.055] px-4 py-2.5 shadow-[0_10px_40px_rgba(0,0,0,0.16)]">
                <span className="text-sm font-semibold text-white">{presentation.tag}</span>
                <span className="ml-2 text-sm text-violet-200">{asPercent(score.value)}</span>
              </div>
            );
          })}
        </div>
      </GlowPanel>

      <div className="space-y-14">
        {groups.map((group) => (
          <ScoreSection key={group.title} title={group.title} description={group.description} scores={group.scores} />
        ))}
      </div>
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

function displayPeriodLabel(label: string | undefined, period: ScorePeriod) {
  if (period === "rolling_year") return "Rolling Year";
  return label ?? "Selected Period";
}

function ScoreSection({ title, description, scores }: { title: string; description: string; scores: ScoreMetric[] }) {
  if (!scores.length) return null;
  return (
    <section>
      <div className="mb-6 max-w-3xl">
        <h2 className="text-3xl font-black text-white">{title}</h2>
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
