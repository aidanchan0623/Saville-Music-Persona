import type { ScoreMetric } from "../types/api";
import { asPercent } from "../utils/format";

export function ScoreGauge({ score }: { score: ScoreMetric }) {
  const degree = Math.min(100, Math.max(0, score.value)) * 3.6;
  return (
    <article className="rounded-lg border border-line bg-panel/82 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-white">{score.name}</h3>
          <p className="mt-1 text-sm text-violet-200">{score.label}</p>
        </div>
        <div
          className="grid h-20 w-20 shrink-0 place-items-center rounded-full"
          style={{
            background: `conic-gradient(#a78bfa ${degree}deg, rgba(255,255,255,0.09) ${degree}deg)`,
          }}
        >
          <div className="grid h-14 w-14 place-items-center rounded-full bg-panel text-sm font-bold text-white">{asPercent(score.value)}</div>
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-mist">{score.explanation}</p>
      <details className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] p-3">
        <summary className="cursor-pointer text-sm font-medium text-white">How this is calculated</summary>
        <p className="mt-3 text-sm text-mist">{score.formula}</p>
        <pre className="mt-3 overflow-auto rounded-md bg-black/25 p-3 text-xs text-mist">{JSON.stringify(score.inputs, null, 2)}</pre>
      </details>
    </article>
  );
}

