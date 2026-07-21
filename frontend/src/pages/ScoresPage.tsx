import { useEffect, useState } from "react";
import { api } from "../api/client";
import { PageTitlePanel } from "../components/PageTitlePanel";
import { getScoreKind, ScoreGauge, type ScoreKind } from "../components/ScoreGauge";
import type { ListeningMinutes, MusicSource, ScoreMetric } from "../types/api";

type ScorePeriod = "this_month" | "month" | "rolling_year";

export function ScoresPage({ scores: initialScores, source, titleAnimationKey }: { scores: ScoreMetric[]; source: MusicSource; titleAnimationKey: string }) {
  const [period, setPeriod] = useState<ScorePeriod>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [scores, setScores] = useState<ScoreMetric[]>(initialScores);
  const [minutes, setMinutes] = useState<ListeningMinutes | null>(null);
  const [loading, setLoading] = useState(false);
  const [openScoreKey, setOpenScoreKey] = useState<string | null>(null);

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
        <p className="border-t border-white/10 pt-5 text-sm text-mist">No scorecard yet.</p>
      </div>
    );
  }
  const primaryScore = pickPrimaryScore(scores);
  const secondaryScores = scores.filter((score) => score.key !== primaryScore.key);
  const groups = buildScoreGroups(secondaryScores);
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
          <p className="max-w-3xl text-xl font-semibold leading-snug text-red-100">{periodLabel} read on replay, discovery, artist pull, and taste shape.</p>
        }
        subtitleClassName="mt-5"
        actions={
          <div className="flex flex-wrap items-center gap-2">
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

      <section className="text-sm text-mist">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-white/10 pt-4">
          <span className="font-semibold text-white">Analysing {periodLabel}</span>
          {loading ? <span>Updating...</span> : null}
          {source === "spotify" ? <span>Spotify top-item based</span> : null}
          {limitedSample ? <span className="text-amber-100">Limited sample for this month</span> : null}
        </div>
      </section>

      <section>
        <ScoreGauge
          score={primaryScore}
          featured
          open={openScoreKey === primaryScore.key}
          onToggle={() => setOpenScoreKey((current) => (current === primaryScore.key ? null : primaryScore.key))}
        />
      </section>

      <div className="space-y-14">
        {groups.map((group) => (
          <ScoreSection
            key={group.title}
            title={group.title}
            scores={group.scores}
            openScoreKey={openScoreKey}
            onToggleScore={(key) => setOpenScoreKey((current) => (current === key ? null : key))}
          />
        ))}
      </div>
    </div>
  );
}

function PeriodButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className={`rounded-md px-3 py-2 text-sm font-semibold transition ${active ? "bg-redPrimary text-white" : "text-mist hover:bg-white/10 hover:text-white"}`} onClick={onClick}>
      {label}
    </button>
  );
}

function displayPeriodLabel(label: string | undefined, period: ScorePeriod) {
  if (period === "rolling_year") return "Rolling Year";
  return label ?? "Selected Period";
}

function ScoreSection({
  title,
  scores,
  openScoreKey,
  onToggleScore,
}: {
  title: string;
  scores: ScoreMetric[];
  openScoreKey: string | null;
  onToggleScore: (key: string) => void;
}) {
  if (!scores.length) return null;
  return (
    <section>
      <div className="mb-5 max-w-3xl">
        <h2 className="text-3xl font-black text-white">{title}</h2>
      </div>
      <div className="grid gap-5 lg:grid-cols-2">
        {scores.map((score) => {
          const kind = getScoreKind(score);
          return (
            <ScoreGauge
              key={score.key}
              score={score}
              featured={kind === "repeat" || kind === "broadCluster"}
              open={openScoreKey === score.key}
              onToggle={() => onToggleScore(score.key)}
            />
          );
        })}
      </div>
    </section>
  );
}

function pickPrimaryScore(scores: ScoreMetric[]) {
  return (
    scores.find((score) => getScoreKind(score) === "tasteConfidence") ??
    scores.find((score) => getScoreKind(score) === "repeat") ??
    scores[0]
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
      scores: listeningHabits,
    },
    {
      title: "Taste Shape",
      scores: tasteShape,
    },
    {
      title: "Positioning",
      scores: [...positioning, ...remaining],
    },
  ].filter((group) => group.scores.length);
}
