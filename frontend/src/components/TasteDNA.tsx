import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { MusicSource, TasteDNA as TasteDNAType, TasteDnaExplorer, TasteDnaNode, TasteInterpretation, TasteTraitNode } from "../types/api";
import { LineWaves } from "./LineWaves";
import { PeriodSelector, type PeriodValue, standardPeriodOptions } from "./ui/PeriodSelector";

interface Props {
  dna: TasteDNAType | null | undefined;
  interpretation?: TasteInterpretation | null;
  source: MusicSource;
}

interface DisplayNode {
  id: string;
  name: string;
  share: number;
  size: number;
  x: number;
  y: number;
  layer: string;
  detectedMinutes: string;
  topArtists: { name: string; plays: number }[];
  topSongs: { name: string; plays: number }[];
  canonicalGenres: string[];
  sonicTraits: string[];
  confidence: number;
  role: string;
}

const TRAIT_GROUPS = [
  {
    label: "Energy",
    patterns: ["energy", "anthem", "cathartic", "heavy", "aggression", "driving", "fast", "punchy", "festival", "restless"],
  },
  {
    label: "Texture",
    patterns: ["atmospheric", "guitar", "polished", "production", "electronic", "cinematic", "hazy", "textural", "orchestral", "dreamy"],
  },
  {
    label: "Mood",
    patterns: ["dramatic", "nostalgic", "melodic", "melancholic", "romantic", "sentimental", "introspective", "late-night", "emotional"],
  },
];

const fallbackPositions = [
  [42, 42],
  [68, 28],
  [22, 31],
  [63, 67],
  [31, 70],
  [79, 55],
] as const;

export function TasteDNA({ dna, interpretation, source }: Props) {
  const [period, setPeriod] = useState<PeriodValue>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [explorer, setExplorer] = useState<TasteDnaExplorer | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.tasteDna(period, period === "month" ? selectedMonth : null, source)
      .then((next) => {
        if (cancelled) return;
        setExplorer(next);
        if (!selectedMonth && next.period.available_months.length) {
          setSelectedMonth(next.period.available_months[next.period.available_months.length - 1].value);
        }
      })
      .catch(() => {
        if (!cancelled) setExplorer(null);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth, source]);

  const fallbackCore = dna?.core_dna?.length ? dna.core_dna.join(" / ") : interpretation?.core_genre_families?.map((item) => item.name).join(" / ");
  const displayNodes = useMemo(() => normaliseNodes(explorer?.nodes, interpretation), [explorer?.nodes, interpretation]);
  const traits = useMemo(() => normaliseTraits(explorer?.traits, dna, interpretation), [dna, explorer?.traits, interpretation]);
  const groupedTraits = useMemo(() => groupTraits(traits), [traits]);
  const months = explorer?.period.available_months ?? [];
  const identity = explorer?.core_identity ?? fallbackCore ?? "Mapped listening core";
  const activeLabel = period === "rolling_year" ? "Rolling Year" : explorer?.period.label ?? periodLabel(period);
  const selectedNode = displayNodes.find((node) => node.id === selectedId) ?? displayNodes[0] ?? null;
  const limitedMonthlySample = Boolean(explorer?.sample_warning && period !== "rolling_year");

  useEffect(() => {
    if (!displayNodes.length) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !displayNodes.some((node) => node.id === selectedId)) {
      setSelectedId(displayNodes[0].id);
    }
  }, [displayNodes, selectedId]);

  if (!dna && !interpretation && !explorer) return null;

  return (
    <section className="relative overflow-hidden rounded-lg border border-white/10 bg-[linear-gradient(135deg,rgba(24,8,8,0.96),rgba(5,3,3,0.99)_58%,rgba(13,6,6,0.98))] shadow-glow">
      <LineWaves className="opacity-55" amplitude={18} speed={0.0001} waveCount={5} />
      <div className="relative border-b border-white/10 p-5 md:p-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-5xl">
            <p className="section-label">Taste DNA</p>
            <h2 className="mt-4 font-display text-4xl uppercase leading-[0.9] tracking-[0.03em] text-white md:text-6xl">{identity}</h2>
            <p className="mt-5 max-w-3xl text-base leading-8 text-mist md:text-lg">
              {buildIdentitySentence(identity, displayNodes, traits)}
            </p>
          </div>
          <PeriodSelector value={period} onChange={setPeriod} month={selectedMonth} months={months} onMonthChange={setSelectedMonth} options={standardPeriodOptions} />
        </div>

        {limitedMonthlySample ? (
          <p className="mt-5 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">
            Limited monthly sample. This view may be shaped by short-term spikes.
          </p>
        ) : null}
      </div>

      <div className="relative grid gap-0 xl:grid-cols-[1.12fr_0.88fr]">
        <div className="border-b border-white/10 p-5 md:p-8 xl:border-b-0 xl:border-r">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist/60">Sound map</p>
              <h3 className="mt-2 text-3xl font-black text-white">{activeLabel}</h3>
            </div>
            <p className="max-w-sm text-sm leading-6 text-mist">Node size follows listening share. Select a node to inspect artists, tracks, genres, and traits.</p>
          </div>

          {displayNodes.length ? (
            <div className="relative mt-7 min-h-[30rem] overflow-hidden rounded-lg border border-white/10 bg-black/25">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(239,68,68,0.12),transparent_34%)]" />
              <div className="absolute left-1/2 top-8 h-[calc(100%-4rem)] w-px bg-white/10" />
              <div className="absolute left-8 top-1/2 h-px w-[calc(100%-4rem)] bg-white/10" />
              {displayNodes.map((node, index) => {
                const diameter = Math.min(9.5, Math.max(4.2, node.size));
                const selected = selectedNode?.id === node.id;
                return (
                  <button
                    key={node.id}
                    type="button"
                    className={`absolute grid -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border text-center transition focus:outline-none focus-visible:ring-2 focus-visible:ring-red-300 ${
                      selected ? "border-red-200 bg-red-600 text-white shadow-[0_0_54px_rgba(239,68,68,0.42)]" : "border-red-300/20 bg-red-950/65 text-red-100 hover:border-red-200/60 hover:bg-red-700/70"
                    }`}
                    style={{ left: `${node.x}%`, top: `${node.y}%`, width: `${diameter}rem`, height: `${diameter}rem` }}
                    onClick={() => setSelectedId(node.id)}
                  >
                    <span className="px-2 text-xs font-black leading-tight md:text-sm">{node.name}</span>
                    <span className="absolute -right-1 -top-1 rounded-full border border-white/10 bg-black px-2 py-1 text-[0.65rem] font-black text-white">{index + 1}</span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="mt-7 rounded-lg border border-white/10 bg-white/[0.04] p-5 text-sm leading-6 text-mist">
              Sound-family data is unavailable for this period, but the overview still has enough evidence to describe the broad profile.
            </div>
          )}
        </div>

        <div className="p-5 md:p-8">
          {selectedNode ? <NodeDetail node={selectedNode} /> : null}

          <div className="mt-7">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist/60">Sonic traits</p>
            <div className="mt-4 space-y-5">
              {groupedTraits.length ? groupedTraits.map((group) => <TraitGroup key={group.label} label={group.label} traits={group.traits} />) : <p className="text-sm text-mist">No confident trait set yet.</p>}
            </div>
          </div>

          <div className="mt-7 rounded-lg border border-red-500/15 bg-white/[0.045] p-5">
            <h3 className="text-lg font-black text-white">What this means</h3>
            <p className="mt-3 text-sm leading-7 text-mist">{buildProfileExplanation(displayNodes, traits, explorer?.summary)}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function NodeDetail({ node }: { node: DisplayNode }) {
  return (
    <article className="rounded-lg border border-white/10 bg-white/[0.04] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200/80">{node.layer || "Signal"}</p>
          <h3 className="mt-2 text-3xl font-black leading-tight text-white">{node.name}</h3>
        </div>
        <div className="text-right">
          <p className="text-3xl font-black text-white">{node.share}%</p>
          <p className="text-xs uppercase tracking-[0.14em] text-mist/70">profile share</p>
        </div>
      </div>
      <p className="mt-4 text-sm leading-7 text-mist">{node.role || "This node describes a recurring sound family in your listening history."}</p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <MiniList title="Top artists" items={node.topArtists.map((artist) => `${artist.name} (${artist.plays})`)} />
        <MiniList title="Top songs" items={node.topSongs.map((song) => `${song.name} (${song.plays})`)} />
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        {node.canonicalGenres.slice(0, 6).map((genre) => <span key={genre} className="subtle-pill">{genre}</span>)}
        {node.sonicTraits.slice(0, 5).map((trait) => <span key={trait} className="subtle-pill border-red-400/20 bg-red-500/10 text-red-100">{trait}</span>)}
      </div>
      <p className="mt-4 text-xs leading-5 text-mist/70">
        {node.detectedMinutes ? `${node.detectedMinutes} detected minutes.` : "Minute coverage unavailable."} Confidence {Math.round(node.confidence)}%.
      </p>
    </article>
  );
}

function MiniList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/60">{title}</p>
      <div className="mt-3 space-y-2">
        {items.length ? items.slice(0, 4).map((item) => <p key={item} className="truncate text-sm text-white">{item}</p>) : <p className="text-sm text-mist">Not enough evidence yet</p>}
      </div>
    </div>
  );
}

function TraitGroup({ label, traits }: { label: string; traits: TasteTraitNode[] }) {
  if (!traits.length) return null;
  return (
    <div>
      <h4 className="text-sm font-semibold text-white">{label}</h4>
      <div className="mt-3 flex flex-wrap gap-2">
        {traits.map((trait) => (
          <span
            key={`${label}-${trait.trait}`}
            title={trait.explanation || undefined}
            className="rounded-full border border-white/10 bg-white/[0.055] px-3 py-1.5 text-sm text-mist"
          >
            {trait.trait}
          </span>
        ))}
      </div>
    </div>
  );
}

function normaliseNodes(nodes: TasteDnaNode[] | undefined, interpretation?: TasteInterpretation | null): DisplayNode[] {
  if (nodes?.length) {
    return nodes.slice(0, 6).map((node) => ({
      id: node.id,
      name: node.name,
      share: node.share,
      size: Math.min(9.5, Math.max(4.2, 3.8 + node.share / 3.6)),
      x: node.x,
      y: node.y,
      layer: roleLabel(node.layer),
      detectedMinutes: node.detected_minutes_formatted,
      topArtists: node.top_artists,
      topSongs: node.top_songs,
      canonicalGenres: node.canonical_genres,
      sonicTraits: node.sonic_traits,
      confidence: node.confidence,
      role: node.role,
    }));
  }

  const clusters = interpretation?.cluster_shares?.length ? interpretation.cluster_shares : interpretation?.core_genre_families ?? [];
  return clusters.slice(0, 6).map((cluster, index) => ({
    id: `fallback-${cluster.name}`,
    name: cluster.name,
    share: Math.round(cluster.share || cluster.value || 0),
    size: Math.min(9, Math.max(4.2, 4 + (cluster.share || cluster.value || 0) / 4)),
    x: fallbackPositions[index]?.[0] ?? 50,
    y: fallbackPositions[index]?.[1] ?? 50,
    layer: index < 2 ? "Core" : index < 4 ? "Influence" : "Side Interest",
    detectedMinutes: "",
    topArtists: [],
    topSongs: [],
    canonicalGenres: [cluster.name],
    sonicTraits: interpretation?.sonic_traits?.slice(0, 4) ?? [],
    confidence: interpretation?.coverage.genre_coverage_percent ?? 0,
    role: "Fallback overview signal from mapped genre shares.",
  }));
}

function normaliseTraits(
  traits: TasteTraitNode[] | undefined,
  dna?: TasteDNAType | null,
  interpretation?: TasteInterpretation | null,
): TasteTraitNode[] {
  if (traits?.length) return traits.slice(0, 14);
  const labels = [...(dna?.sonic_traits ?? []), ...(interpretation?.sonic_traits ?? [])];
  return Array.from(new Set(labels)).slice(0, 12).map((trait) => ({
    trait,
    support_percent: 0,
    confidence: "overview",
    supporting_artists: [],
    supporting_clusters: [],
    explanation: "Trait inferred from overview-level taste evidence.",
  }));
}

function groupTraits(traits: TasteTraitNode[]) {
  const used = new Set<string>();
  const groups = TRAIT_GROUPS.map((group) => {
    const matched = traits.filter((trait) => {
      const text = trait.trait.toLowerCase();
      return group.patterns.some((pattern) => text.includes(pattern));
    });
    matched.forEach((trait) => used.add(trait.trait));
    return { label: group.label, traits: matched.slice(0, 5) };
  });
  const remaining = traits.filter((trait) => !used.has(trait.trait)).slice(0, 5);
  if (remaining.length) {
    const mood = groups.find((group) => group.label === "Mood");
    if (mood) mood.traits = [...mood.traits, ...remaining].slice(0, 6);
  }
  return groups.filter((group) => group.traits.length);
}

function roleLabel(layer: string) {
  if (layer === "Side Quest" || layer === "Trace") return "Side Interest";
  return layer || "Signal";
}

function periodLabel(period: PeriodValue) {
  return standardPeriodOptions.find((option) => option.value === period)?.label ?? "Selected Period";
}

function buildIdentitySentence(identity: string, nodes: DisplayNode[], traits: TasteTraitNode[]) {
  const core = nodes[0]?.name ?? identity;
  const secondary = nodes.slice(1, 4).map((node) => node.name);
  const topTraits = traits.slice(0, 2).map((trait) => trait.trait);
  if (secondary.length || topTraits.length) {
    const branches = secondary.length ? secondary : topTraits;
    return `Your listening has a clear ${core} centre, with ${formatInlineList(branches)} shaping the profile.`;
  }
  return "Your listening profile is still forming from the available mapped artists and detected plays.";
}

function buildProfileExplanation(nodes: DisplayNode[], traits: TasteTraitNode[], fallback?: string | null) {
  if (nodes.length) {
    const core = nodes[0].name;
    const branches = nodes.slice(1, 5).map((node) => node.name);
    const traitText = traits.slice(0, 3).map((trait) => trait.trait);
    return `Your profile has a clear ${core} home base, with ${formatInlineList(branches.length ? branches : traitText)} adding shape around it.`;
  }
  return fallback || "The app needs more mapped listening data before it can describe a reliable sound profile for this period.";
}

function formatInlineList(items: string[]) {
  const clean = items.filter(Boolean);
  if (clean.length <= 1) return clean[0] ?? "nearby sound families";
  if (clean.length === 2) return `${clean[0]} and ${clean[1]}`;
  return `${clean.slice(0, -1).join(", ")} and ${clean[clean.length - 1]}`;
}
