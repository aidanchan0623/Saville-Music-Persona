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
  body: string;
  evidenceLine: string;
}

export function ScoreGauge({ score, featured = false }: { score: ScoreMetric; featured?: boolean }) {
  const presentation = getScorePresentation(score);
  const degree = Math.min(100, Math.max(0, score.value)) * 3.6;
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
          className="grid h-20 w-20 shrink-0 place-items-center rounded-full shadow-[0_0_40px_rgba(239,68,68,0.2)] md:h-24 md:w-24"
          style={{
            background: `conic-gradient(#ef4444 0deg, #dc2626 ${degree}deg, rgba(255,255,255,0.09) ${degree}deg)`,
          }}
        >
          <div className="grid h-14 w-14 place-items-center rounded-full bg-[#090505] text-sm font-black text-white md:h-16 md:w-16">{asPercent(score.value)}</div>
        </div>
      </div>

      <div className="relative mt-5 max-w-3xl">
        <p className="text-base leading-7 text-mist">{presentation.body}</p>
        <p className="mt-4 border-l border-violet/35 pl-4 text-sm leading-6 text-mist/85">{presentation.evidenceLine}</p>
      </div>
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
      body: "You come back to songs strongly once they land. Your listening is less about constantly chasing new tracks and more about finding songs that fit your mood, then keeping them in rotation.",
      evidenceLine: "Based on repeated tracks across the selected period.",
    };
  }
  if (kind === "artistLoyalty") {
    return {
      kind,
      displayName: "Artist loyalty",
      tag: "Broadly roaming",
      headline: "Broadly roaming, not artist-locked",
      body: "You are not built around only one or two artists. The sound world is consistent, but the artists rotate enough that your profile feels sound-led rather than fandom-led.",
      evidenceLine: "Based on how plays are distributed across your top artists.",
    };
  }
  if (kind === "discovery") {
    return {
      kind,
      displayName: "Discovery score",
      tag: "Selective explorer",
      headline: "Selective explorer",
      body: "New music appears in your listening, but trusted favourites still lead. You explore, just not at the expense of the songs and artists that already work for you.",
      evidenceLine: "Based on newer listening signals compared with established repeats.",
    };
  }
  if (kind === "nostalgia") {
    return {
      kind,
      displayName: "Nostalgia score",
      tag: hasWeakEraMetadata ? "Era preference unclear" : "Mostly current-facing",
      headline: hasWeakEraMetadata ? "Era preference unclear" : "Mostly current-facing",
      body: hasWeakEraMetadata
        ? "Release-year evidence is too partial to read this strongly, so this score stays cautious instead of pretending to know your era preference."
        : "Newer music shapes more of your detected listening, while older songs can still matter as part of the profile without becoming the main centre.",
      evidenceLine: "Based on release-year metadata where it is available.",
    };
  }
  if (kind === "broadCluster") {
    return {
      kind,
      displayName: "Broad-cluster diversity",
      tag: "Rock-centred, internally varied",
      headline: "Rock-centred, internally varied",
      body: "Your taste has a clear home base, but it is not one-dimensional. The variation happens inside connected alternative, rock, emo, heavy and atmospheric worlds.",
      evidenceLine: "Based on the spread across mapped broad sound families.",
    };
  }
  if (kind === "withinCluster") {
    return {
      kind,
      displayName: "Within-cluster diversity",
      tag: "Deep within your lane",
      headline: "Deep within your lane",
      body: "Your listening stays inside recognisable lanes, but those lanes still contain multiple textures and substyles. It reads as focus with depth, not a flat one-note pattern.",
      evidenceLine: "Based on variety inside the strongest mapped sound families.",
    };
  }
  if (kind === "mainstreamNiche") {
    return {
      kind,
      displayName: "Mainstream-Niche Estimate",
      tag: "Niche-leaning",
      headline: "Niche-leaning listener",
      body: "Your detected artists lean away from the most obvious mainstream centre. This does not mean obscure for the sake of obscure - just that chart gravity is not the default force in your listening.",
      evidenceLine: "Based on available popularity and artist metadata, treated as a cautious estimate.",
    };
  }
  if (kind === "tasteConfidence") {
    return {
      kind,
      displayName: "Profile signal",
      tag: "Strong profile signal",
      headline: "Strong profile signal",
      body: "The app has enough listening and metadata signal to make a coherent profile, while still keeping uncertainty visible where the source data is thin.",
      evidenceLine: "Based on how much listening history and music metadata is available.",
    };
  }
  return {
    kind,
    displayName: score.name,
    tag: score.name,
    headline: score.interpretation?.status_title ?? score.label,
    body: score.interpretation?.plain_english ?? score.explanation,
    evidenceLine: score.interpretation?.evidence?.[0] ?? "Based on the available listening profile evidence.",
  };
}
