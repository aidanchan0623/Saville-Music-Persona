import type { ScoreMetric } from "../types/api";
import { asPercent } from "../utils/format";

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
  summary: string;
  bullets: string[];
}

export function ScoreGauge({ score, featured = false }: { score: ScoreMetric; featured?: boolean }) {
  const presentation = getScorePresentation(score);
  const degree = Math.min(100, Math.max(0, score.value)) * 3.6;
  const confidenceNote = score.interpretation?.confidence;
  const confidenceInput = typeof score.inputs.confidence_note === "string" ? score.inputs.confidence_note : null;
  return (
    <article
      className={`relative overflow-hidden rounded-[1.35rem] border border-white/10 bg-[linear-gradient(145deg,rgba(255,255,255,0.065),rgba(255,255,255,0.025))] p-5 shadow-[0_18px_70px_rgba(0,0,0,0.22)] transition hover:border-violet/25 hover:bg-white/[0.055] md:p-6 ${
        featured ? "lg:col-span-2" : ""
      }`}
    >
      <div className="absolute -right-12 -top-16 h-40 w-40 rounded-full bg-violet/15 blur-3xl" />
      <div className="relative flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-200">{presentation.displayName}</p>
          <h3 className="mt-3 text-2xl font-black leading-tight text-white md:text-3xl">{presentation.headline}</h3>
        </div>
        <div
          className="grid h-20 w-20 shrink-0 place-items-center rounded-full shadow-[0_0_40px_rgba(139,92,246,0.2)] md:h-24 md:w-24"
          style={{
            background: `conic-gradient(#d946ef 0deg, #a78bfa ${degree}deg, rgba(255,255,255,0.09) ${degree}deg)`,
          }}
        >
          <div className="grid h-14 w-14 place-items-center rounded-full bg-[#0b0b15] text-sm font-black text-white md:h-16 md:w-16">{asPercent(score.value)}</div>
        </div>
      </div>

      <div className="relative mt-5 max-w-3xl">
        <p className="text-base leading-7 text-mist">{presentation.summary}</p>
        <div className="mt-5 border-l border-violet/35 pl-4">
          <p className="text-sm font-semibold text-violet-100">What this means</p>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-mist">
            {presentation.bullets.map((item) => (
              <li key={item} className="flex gap-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-violet" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="relative mt-5 flex flex-wrap gap-2 text-xs">
        {confidenceNote ? <span className="rounded-full bg-white/[0.06] px-3 py-1.5 text-mist">Confidence: {confidenceNote}</span> : null}
        {confidenceInput ? <span className="rounded-full bg-violet/10 px-3 py-1.5 text-violet-100">{confidenceInput}</span> : null}
      </div>

      <details className="relative mt-5 rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
        <summary className="cursor-pointer text-sm font-semibold text-white">Why this score landed here</summary>
        <p className="mt-3 text-sm leading-6 text-mist">{score.formula}</p>
        {score.interpretation?.evidence?.length ? (
          <ul className="mt-3 space-y-2 text-sm leading-6 text-mist">
            {score.interpretation.evidence.map((item) => (
              <li key={item}>- {item}</li>
            ))}
          </ul>
        ) : null}
        {Object.keys(score.inputs).length ? (
          <dl className="mt-4 grid gap-2 text-xs text-mist sm:grid-cols-2">
            {Object.entries(score.inputs).map(([key, value]) => (
              <div key={key} className="rounded-xl bg-white/[0.04] p-3">
                <dt className="uppercase tracking-[0.14em] text-mist/60">{formatInputLabel(key)}</dt>
                <dd className="mt-1 break-words text-white/85">{formatInputValue(value)}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </details>
    </article>
  );
}

export function getScoreKind(score: ScoreMetric): ScoreKind {
  const identity = `${score.key} ${score.name}`.toLowerCase();
  if (identity.includes("repeat")) return "repeat";
  if (identity.includes("discovery")) return "discovery";
  if (identity.includes("loyal")) return "artistLoyalty";
  if (identity.includes("broad") && identity.includes("cluster")) return "broadCluster";
  if (identity.includes("within") && identity.includes("cluster")) return "withinCluster";
  if (identity.includes("nostalgia") || identity.includes("release") || identity.includes("era")) return "nostalgia";
  if (identity.includes("mainstream") || identity.includes("niche")) return "mainstreamNiche";
  if (score.key === "taste_confidence" || identity.includes("taste confidence")) return "tasteConfidence";
  return "other";
}

export function getScorePresentation(score: ScoreMetric): ScorePresentation {
  const kind = getScoreKind(score);
  const hasWeakEraMetadata = kind === "nostalgia" && /low|limited|partial/i.test(score.interpretation?.confidence ?? "");

  if (kind === "repeat") {
    return {
      kind,
      displayName: "Repeat score",
      tag: "Replay-heavy listener",
      headline: "Replay-heavy listener",
      summary: "Songs stay in rotation once they hit.",
      bullets: [
        "Favourites are allowed to build weight instead of being replaced instantly.",
        "The score reads repetition as a listening habit, not as a value judgement.",
        "The ring uses the existing repeat score from your listening profile.",
      ],
    };
  }
  if (kind === "artistLoyalty") {
    return {
      kind,
      displayName: "Artist loyalty",
      tag: "Broadly roaming",
      headline: "Broadly roaming, not artist-locked",
      summary: "You follow a sound more than a tiny roster of artists.",
      bullets: [
        "The profile is not dependent on only one or two artist obsessions.",
        "Your centre appears more sonic than roster-bound.",
        "Artist attachment is read from the existing play distribution.",
      ],
    };
  }
  if (kind === "discovery") {
    return {
      kind,
      displayName: "Discovery score",
      tag: "Selective explorer",
      headline: "Selective explorer",
      summary: "New music appears, but trusted favourites still lead.",
      bullets: [
        "You make room for newer or less familiar tracks.",
        "Exploration does not overpower the comfort layer of the profile.",
        "The score balances recent arrivals against established listening.",
      ],
    };
  }
  if (kind === "nostalgia") {
    return {
      kind,
      displayName: "Nostalgia score",
      tag: hasWeakEraMetadata ? "Era preference unclear" : "Mostly current-facing",
      headline: hasWeakEraMetadata ? "Era preference unclear" : "Mostly current-facing",
      summary: hasWeakEraMetadata ? "Release-year evidence is too partial to read this strongly." : "Newer music shapes more of your detected listening.",
      bullets: [
        "The read depends on available release-year metadata.",
        "Older songs can still matter without becoming the main centre.",
        "The details panel keeps the era-evidence limits visible.",
      ],
    };
  }
  if (kind === "broadCluster") {
    return {
      kind,
      displayName: "Broad-cluster diversity",
      tag: "Rock-centred, internally varied",
      headline: "Rock-centred, internally varied",
      summary: "Your taste has a clear home base, but several connected substyles.",
      bullets: [
        "The profile has a recognisable centre instead of scattered randomness.",
        "Variation happens through connected rock and alternative-adjacent worlds.",
        "Genre coverage shapes how confidently the breadth can be read.",
      ],
    };
  }
  if (kind === "withinCluster") {
    return {
      kind,
      displayName: "Within-cluster diversity",
      tag: "Deep within your lane",
      headline: "Deep within your lane",
      summary: "Focused, but not one-dimensional.",
      bullets: [
        "Your listening stays inside recognisable lanes.",
        "Those lanes still contain multiple textures and substyles.",
        "The score reads variety inside the strongest taste families.",
      ],
    };
  }
  if (kind === "mainstreamNiche") {
    return {
      kind,
      displayName: "Mainstream-Niche Estimate",
      tag: "Niche-leaning",
      headline: "Niche-leaning listener",
      summary: "Broadly popular chart gravity is not your default centre.",
      bullets: [
        "Popularity metadata is treated as a cautious proxy, not a judgement.",
        "The read points to a centre outside obvious chart defaults.",
        "Uncertainty stays visible when subscriber metadata coverage is thin.",
      ],
    };
  }
  if (kind === "tasteConfidence") {
    return {
      kind,
      displayName: "Taste confidence",
      tag: "Strong profile signal",
      headline: "Strong profile signal",
      summary: "Useful, but shaped by available metadata coverage.",
      bullets: [
        "The app has enough signal to make a coherent profile.",
        "Metadata gaps still limit some fine-grained claims.",
        "This is a data-quality score, not a score of your taste.",
      ],
    };
  }
  return {
    kind,
    displayName: score.name,
    tag: score.name,
    headline: score.interpretation?.status_title ?? score.label,
    summary: score.interpretation?.plain_english ?? score.explanation,
    bullets: [
      score.explanation,
      score.interpretation?.confidence ? `Confidence: ${score.interpretation.confidence}` : "Open the details panel for the exact evidence.",
    ].filter(Boolean),
  };
}

function formatInputLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatInputValue(value: unknown) {
  if (value === null || value === undefined) return "Unavailable";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1);
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return JSON.stringify(value);
}
