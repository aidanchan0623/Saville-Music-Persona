import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { TasteDNA as TasteDNAType, TasteDnaExplorer, TasteDnaNode, TasteInterpretation, TasteTraitNode } from "../types/api";

type TastePeriod = "this_month" | "month" | "rolling_year";

interface Props {
  dna: TasteDNAType | null | undefined;
  interpretation?: TasteInterpretation | null;
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

export function TasteDNA({ dna, interpretation }: Props) {
  const [period, setPeriod] = useState<TastePeriod>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [explorer, setExplorer] = useState<TasteDnaExplorer | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.tasteDna(period, period === "month" ? selectedMonth : null)
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
  }, [period, selectedMonth]);

  const fallbackCore = dna?.core_dna?.length ? dna.core_dna.join(" / ") : interpretation?.core_genre_families?.map((item) => item.name).join(" / ");
  const nodes = (explorer?.nodes ?? []).slice(0, 6);
  const traits = (explorer?.traits ?? []).slice(0, 12);
  const months = explorer?.period.available_months ?? [];
  const identity = explorer?.core_identity ?? fallbackCore ?? "Mapped listening core";
  const activeLabel = period === "rolling_year" ? "Rolling Year" : explorer?.period.label ?? "Selected period";
  const maxShare = useMemo(() => Math.max(...nodes.map((node) => node.share), 1), [nodes]);
  const groupedTraits = useMemo(() => groupTraits(traits), [traits]);
  const limitedMonthlySample = Boolean(explorer?.sample_warning && period !== "rolling_year");

  if (!dna && !interpretation && !explorer) return null;

  return (
    <section className="overflow-hidden rounded-[2rem] border border-red-500/15 bg-[linear-gradient(135deg,rgba(33,10,10,0.96),rgba(5,5,5,0.99)_58%,rgba(18,7,7,0.98))] shadow-glow">
      <div className="relative border-b border-white/10 p-6 lg:p-9">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_0%,rgba(239,68,68,0.22),transparent_34%)]" />
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="relative max-w-5xl">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-red-200">Sound Profile</p>
            <h2 className="mt-4 text-4xl font-black leading-[0.98] text-white md:text-6xl xl:text-7xl">{identity}</h2>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-mist md:text-xl">
              {buildIdentitySentence(identity, nodes, traits)}
            </p>
          </div>
          <div className="relative flex flex-wrap gap-2 rounded-xl border border-white/10 bg-black/25 p-2 shadow-[0_18px_60px_rgba(0,0,0,0.2)]">
            <PeriodButton active={period === "this_month"} label="This Month" onClick={() => setPeriod("this_month")} />
            <PeriodButton active={period === "month"} label="Select Month" onClick={() => setPeriod("month")} />
            <PeriodButton active={period === "rolling_year"} label="Rolling Year" onClick={() => setPeriod("rolling_year")} />
            {period === "month" ? (
              <select className="rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-white" value={selectedMonth ?? months[months.length - 1]?.value ?? ""} onChange={(event) => setSelectedMonth(event.target.value)}>
                {months.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
              </select>
            ) : null}
          </div>
        </div>

        {limitedMonthlySample ? (
          <p className="mt-5 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">
            Limited monthly sample - this view may be shaped by short-term spikes.
          </p>
        ) : null}
      </div>

      <div className="grid gap-0 xl:grid-cols-[1.18fr_0.82fr]">
        <div className="border-b border-white/10 p-6 lg:p-9 xl:border-b-0 xl:border-r">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist/60">Core Sound Breakdown</p>
              <h3 className="mt-2 text-3xl font-black text-white">{activeLabel}</h3>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {nodes.length ? nodes.map((node) => <SoundFamilyRow key={node.id} node={node} maxShare={maxShare} />) : (
              <div className="rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm text-mist">Sound-family data is unavailable for this period.</div>
            )}
          </div>
        </div>

        <div className="p-6 lg:p-9">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-mist/60">Sonic Traits</p>
          <div className="mt-4 space-y-5">
            {groupedTraits.map((group) => (
              <TraitGroup key={group.label} label={group.label} traits={group.traits} />
            ))}
          </div>

          <div className="mt-7 rounded-2xl border border-red-500/15 bg-white/[0.045] p-5">
            <h3 className="text-lg font-black text-white">What this means</h3>
            <p className="mt-3 text-sm leading-7 text-mist">{buildProfileExplanation(nodes, traits, explorer?.summary)}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function PeriodButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className={`rounded-lg px-3 py-2 text-sm font-semibold ${active ? "bg-red-600 text-white" : "text-mist hover:bg-white/10 hover:text-white"}`} onClick={onClick}>
      {label}
    </button>
  );
}

function SoundFamilyRow({ node, maxShare }: { node: TasteDnaNode; maxShare: number }) {
  const width = Math.max(8, (node.share / maxShare) * 100);
  const artists = node.top_artists.slice(0, 3).map((artist) => artist.name).join(", ");
  return (
    <article className="rounded-2xl border border-white/10 bg-white/[0.045] p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="text-xl font-black text-white">{node.name}</h4>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-2.5 py-1 text-xs font-semibold text-red-100">{roleLabel(node.layer)}</span>
          </div>
          <p className="mt-2 text-sm leading-6 text-mist">{artists ? `Top contributors: ${artists}.` : "Top contributing artists are unavailable for this period."}</p>
        </div>
        <div className="shrink-0 text-left md:text-right">
          <p className="text-3xl font-black text-white">{node.share}%</p>
          <p className="text-xs uppercase tracking-[0.14em] text-mist/70">of profile</p>
        </div>
      </div>
      <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-white/10">
        <div className="h-full rounded-full bg-gradient-to-r from-red-700 via-red-500 to-red-200" style={{ width: `${width}%` }} />
      </div>
    </article>
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

function buildIdentitySentence(identity: string, nodes: TasteDnaNode[], traits: TasteTraitNode[]) {
  const core = nodes[0]?.name ?? identity;
  const secondary = nodes.slice(1, 4).map((node) => node.name);
  const topTraits = traits.slice(0, 2).map((trait) => trait.trait);
  if (secondary.length || topTraits.length) {
    const branches = secondary.length ? secondary : topTraits;
    return `Your listening has a clear ${core} centre, with ${formatInlineList(branches)} shaping the profile.`;
  }
  return "Your listening profile is still forming from the available mapped artists and detected plays.";
}

function buildProfileExplanation(nodes: TasteDnaNode[], traits: TasteTraitNode[], fallback?: string | null) {
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
