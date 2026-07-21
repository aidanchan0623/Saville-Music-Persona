import { useEffect, useId, useState } from "react";
import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import type { ScoreMetric } from "../types/api";
import CountUp from "./reactbits/CountUp/CountUp";
import { GlowPanel } from "./GlowPanel";
import "./ScoreGauge.css";

export type ScoreKind =
  | "repeat"
  | "discovery"
  | "artistLoyalty"
  | "broadCluster"
  | "withinCluster"
  | "nostalgia"
  | "mainstreamNiche"
  | "tasteConfidence"
  | "other";

interface ScorePresentation {
  kind: ScoreKind;
  displayName: string;
  tag: string;
  headline: string;
  measures: string;
  calculation: string;
  resultMeaning: string;
  limitations: string;
}

export function ScoreGauge({
  score,
  featured = false,
  open,
  onToggle,
}: {
  score: ScoreMetric;
  featured?: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  const presentation = getScorePresentation(score);
  const detailsId = useId();
  const value = clampScore(score.value);
  const decimals = Number.isInteger(score.value) ? 0 : 1;

  return (
    <GlowPanel as="article" variant="card" wrapperClassName={featured ? "lg:col-span-2" : ""} className="score-card p-5 md:p-6">
      <div className="score-card__layout">
        <div className="score-card__copy">
          <p className="score-card__eyebrow">{presentation.displayName}</p>
          <h3 className="score-card__title">{presentation.headline}</h3>
          <div className="score-card__number-row" aria-label={`${presentation.displayName}: ${score.value} out of 100`}>
            <CountUp from={0} to={score.value} duration={1.2} separator="," decimals={decimals} className="score-number" />
            <span className="score-card__unit">/100</span>
          </div>
          <p className="score-card__tag">{presentation.tag}</p>
        </div>
        <ScoreRadialChart label={presentation.displayName} value={value} />
      </div>

      <ScoreDetails id={detailsId} open={open} onToggle={onToggle} presentation={presentation} score={score} />
    </GlowPanel>
  );
}

function ScoreRadialChart({ label, value }: { label: string; value: number }) {
  const reducedMotion = useReducedMotion();
  const data = [{ name: label, value, fill: "#e52b32" }];
  return (
    <div className="score-radial" aria-hidden="true">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart data={data} startAngle={90} endAngle={-270} innerRadius="72%" outerRadius="96%">
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="value" background={{ fill: "rgba(255,255,255,0.08)" }} cornerRadius={10} fill="#e52b32" isAnimationActive={!reducedMotion} animationDuration={900} />
        </RadialBarChart>
      </ResponsiveContainer>
      <span className="score-radial__center">{Math.round(value)}%</span>
    </div>
  );
}

function ScoreDetails({
  id,
  open,
  onToggle,
  presentation,
  score,
}: {
  id: string;
  open: boolean;
  onToggle: () => void;
  presentation: ScorePresentation;
  score: ScoreMetric;
}) {
  return (
    <div className="score-details-wrap">
      <button className="score-details-button" type="button" aria-expanded={open} aria-controls={id} onClick={onToggle}>
        {open ? "Hide explanation" : "See explanation"}
      </button>
      <div id={id} className={`score-details${open ? " score-details--open" : ""}`}>
        <div className="score-details__inner">
          <DetailBlock title="What it measures" body={presentation.measures} />
          <DetailBlock title="How it is calculated" body={score.formula || presentation.calculation} />
          <DetailBlock title="What your result means" body={score.interpretation?.plain_english || presentation.resultMeaning} />
          <DetailBlock title="Limitations" body={presentation.limitations} />
        </div>
      </div>
    </div>
  );
}

function DetailBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="score-details__block">
      <h4>{title}</h4>
      <p>{body}</p>
    </div>
  );
}

export function getScoreKind(score: ScoreMetric): ScoreKind {
  const identity = `${score.key} ${score.name}`.toLowerCase();
  if (identity.includes("repeat")) return "repeat";
  if (identity.includes("discovery")) return "discovery";
  if (identity.includes("loyal")) return "artistLoyalty";
  if (identity.includes("broad") && identity.includes("cluster")) return "broadCluster";
  if (identity.includes("within") && identity.includes("cluster")) return "withinCluster";
  if (identity.includes("nostalgia") || identity.includes("release" ) || identity.includes("era")) return "nostalgia";
  if (identity.includes("mainstream") || identity.includes("niche")) return "mainstreamNiche";
  if (score.key === "taste_confidence" || identity.includes("taste confidence")) return "tasteConfidence";
  return "other";
}

export function getScorePresentation(score: ScoreMetric): ScorePresentation {
  const kind = getScoreKind(score);
  const hasWeakEraMetadata = kind === "nostalgia" && /low|limited|partial/i.test(score.interpretation?.confidence ?? "");
  const evidence = score.interpretation?.evidence?.[0] ?? "Uses the available local listening profile for the selected period.";

  if (kind === "repeat") {
    return {
      kind,
      displayName: "Repeat score",
      tag: "Replay gravity",
      headline: "Replay-heavy listener",
      measures: "How strongly your period is shaped by returning to the same songs.",
      calculation: "Compares total track plays with unique tracks, then scales that repeat density to a 0-100 score.",
      resultMeaning: "Higher means a smaller set of songs keeps pulling you back.",
      limitations: evidence,
    };
  }
  if (kind === "artistLoyalty") {
    return {
      kind,
      displayName: "Artist loyalty",
      tag: "Artist pull",
      headline: "Sound-led, not artist-locked",
      measures: "How concentrated your listening is around the top artists.",
      calculation: "Looks at play distribution across artists and converts that concentration into a 0-100 loyalty score.",
      resultMeaning: "Higher means a few artists dominate the period; lower means the artists rotate more.",
      limitations: evidence,
    };
  }
  if (kind === "discovery") {
    return {
      kind,
      displayName: "Discovery score",
      tag: "Newness",
      headline: "Selective explorer",
      measures: "How much newer or less-repeated listening appears beside your familiar favourites.",
      calculation: "Balances first-time or lower-repeat signals against established repeats for the selected period.",
      resultMeaning: "Higher means more exploration; lower means comfort listening is leading.",
      limitations: evidence,
    };
  }
  if (kind === "nostalgia") {
    return {
      kind,
      displayName: "Nostalgia score",
      tag: hasWeakEraMetadata ? "Era unclear" : "Era pull",
      headline: hasWeakEraMetadata ? "Era preference unclear" : "Mostly current-facing",
      measures: "How much older release-year metadata appears in the songs with usable era data.",
      calculation: "Uses known release years where available and scales the older-era share to 0-100.",
      resultMeaning: hasWeakEraMetadata ? "The result should be read lightly because release-year coverage is thin." : "Higher means older eras shape more of the profile.",
      limitations: evidence,
    };
  }
  if (kind === "broadCluster") {
    return {
      kind,
      displayName: "Broad-cluster diversity",
      tag: "Genre range",
      headline: "Rock-centred, internally varied",
      measures: "How widely your listening spreads across broad mapped sound families.",
      calculation: "Measures the spread of plays across the detected broad genre clusters and scales it to 0-100.",
      resultMeaning: "Higher means several sound families matter; lower means one family dominates.",
      limitations: evidence,
    };
  }
  if (kind === "withinCluster") {
    return {
      kind,
      displayName: "Within-cluster diversity",
      tag: "Lane depth",
      headline: "Deep within your lane",
      measures: "How much variety exists inside your strongest mapped sound families.",
      calculation: "Looks at substyle variation within dominant clusters, then scores that internal variety.",
      resultMeaning: "Higher means your main lanes contain more texture and substyle shifts.",
      limitations: evidence,
    };
  }
  if (kind === "mainstreamNiche") {
    return {
      kind,
      displayName: "Mainstream-Niche Estimate",
      tag: "Niche lean",
      headline: "Niche-leaning listener",
      measures: "How your artists sit relative to available mainstream popularity signals.",
      calculation: "Uses available popularity and artist metadata as a cautious proxy, then scales the niche tendency to 0-100.",
      resultMeaning: "Higher means your listening leans further from obvious chart gravity.",
      limitations: evidence,
    };
  }
  if (kind === "tasteConfidence") {
    return {
      kind,
      displayName: "Profile signal",
      tag: "Data confidence",
      headline: "Strong profile signal",
      measures: "How much usable listening and metadata exists for a coherent profile.",
      calculation: "Combines listening volume, coverage, and metadata availability into a confidence-style score.",
      resultMeaning: "Higher means the app has enough signal to describe your taste more confidently.",
      limitations: evidence,
    };
  }
  return {
    kind,
    displayName: score.name,
    tag: score.label,
    headline: score.interpretation?.status_title ?? score.label,
    measures: score.explanation || "A deterministic score calculated from the selected listening period.",
    calculation: score.formula || "Calculated from the available local listening and metadata inputs.",
    resultMeaning: score.interpretation?.plain_english ?? score.label,
    limitations: evidence,
  };
}

function clampScore(value: number) {
  return Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
}

function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return reducedMotion;
}
