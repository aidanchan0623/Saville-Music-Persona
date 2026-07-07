import { EmptyState } from "../components/EmptyState";
import { ScoreGauge } from "../components/ScoreGauge";
import type { ScoreMetric } from "../types/api";

export function ScoresPage({ scores }: { scores: ScoreMetric[] }) {
  if (!scores.length) return <EmptyState title="No scorecard yet" body="Refresh data to calculate deterministic scores with transparent formulas." />;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-bold text-white">Taste Scores</h1>
        <p className="mt-2 max-w-3xl text-mist">
          Every number is calculated in the backend. Genre diversity now uses curated broad clusters plus within-cluster variety, so a rock-centred taste can still register as internally varied.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {scores.map((score) => (
          <ScoreGauge key={score.key} score={score} />
        ))}
      </div>
    </div>
  );
}
