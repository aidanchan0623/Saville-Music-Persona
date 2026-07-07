import { EmptyState } from "../components/EmptyState";
import { getScoreKind, getScorePresentation, ScoreGauge, type ScoreKind } from "../components/ScoreGauge";
import type { ScoreMetric } from "../types/api";
import { asPercent } from "../utils/format";

export function ScoresPage({ scores }: { scores: ScoreMetric[] }) {
  if (!scores.length) return <EmptyState title="No scorecard yet" body="Refresh data to calculate deterministic scores with transparent formulas." />;
  const groups = buildScoreGroups(scores);
  const glanceScores = getAtAGlanceScores(scores);

  return (
    <div className="space-y-12">
      <header className="max-w-5xl py-3">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-violet-200">Music listening profile</p>
        <h1 className="mt-4 text-5xl font-black leading-[0.95] tracking-tight text-white md:text-7xl">Taste Scores</h1>
        <p className="mt-5 max-w-3xl text-2xl font-semibold leading-snug text-violet-100">
          A clearer read on how you listen &mdash; not just what you play.
        </p>
        <p className="mt-4 max-w-3xl text-base leading-8 text-mist md:text-lg">
          These scores translate your listening habits into a music profile: how you replay, explore, roam across artists, and shape your own sound world.
        </p>
      </header>

      <section className="flex flex-col gap-4 border-y border-white/10 py-5 lg:flex-row lg:items-center">
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
      </section>

      <div className="space-y-14">
        {groups.map((group) => (
          <ScoreSection key={group.title} title={group.title} description={group.description} scores={group.scores} />
        ))}
      </div>
    </div>
  );
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
