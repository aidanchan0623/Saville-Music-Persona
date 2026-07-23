import { useId } from "react";
import type { ScoreMetric } from "../../types/api";
import { useVisibleMotion } from "./useVisibleMotion";

const CIRCUMFERENCE = 2 * Math.PI * 42;

export function CompactScoreGauge({ score, index }: { score: ScoreMetric; index: number }) {
  const gradientId = useId().replace(/:/g, "");
  const { ref, entered, reducedMotion } = useVisibleMotion();
  const value = clamp(score.value);
  const offset = entered ? CIRCUMFERENCE * (1 - value / 100) : CIRCUMFERENCE;
  const title = score.interpretation?.status_title ?? score.label;

  return (
    <div ref={ref} className="insights-score">
      <div
        className="insights-score__gauge"
        role="progressbar"
        aria-label={score.name}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(value)}
      >
        <svg viewBox="0 0 100 100" aria-hidden="true">
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#ff7b7d" />
              <stop offset="1" stopColor="#c21f25" />
            </linearGradient>
          </defs>
          <circle className="insights-score__track" cx="50" cy="50" r="42" />
          <circle
            className="insights-score__progress"
            cx="50"
            cy="50"
            r="42"
            stroke={`url(#${gradientId})`}
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            style={{ transitionDelay: reducedMotion ? "0ms" : `${index * 70}ms` }}
          />
        </svg>
        <span>{Math.round(value)}</span>
      </div>
      <div className="insights-score__copy">
        <h3>{shortScoreName(score)}</h3>
        <p>{title}</p>
        <details>
          <summary>How this is calculated</summary>
          <p>{score.formula}</p>
        </details>
      </div>
    </div>
  );
}

function shortScoreName(score: ScoreMetric) {
  const names: Record<string, string> = {
    repeat: "Repeat attachment",
    discovery: "Discovery",
    artist_loyalty: "Artist loyalty",
    broad_cluster_diversity: "Diversity",
    mainstream_niche: "Niche lean",
  };
  return names[score.key] ?? score.name;
}

function clamp(value: number) {
  return Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 0;
}
