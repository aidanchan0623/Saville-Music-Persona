import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { TasteDNA as TasteDNAType, TasteDnaComparison, TasteDnaExplorer, TasteDnaNode, TasteInterpretation, TasteTraitNode } from "../types/api";

type TastePeriod = "this_month" | "month" | "rolling_year";

interface Props {
  dna: TasteDNAType | null | undefined;
  interpretation?: TasteInterpretation | null;
}

export function TasteDNA({ dna, interpretation }: Props) {
  const [period, setPeriod] = useState<TastePeriod>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [explorer, setExplorer] = useState<TasteDnaExplorer | null>(null);
  const [comparison, setComparison] = useState<TasteDnaComparison | null>(null);
  const [selectedNode, setSelectedNode] = useState<TasteDnaNode | null>(null);
  const [selectedTrait, setSelectedTrait] = useState<TasteTraitNode | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.tasteDna(period, period === "month" ? selectedMonth : null)
      .then((next) => {
        if (cancelled) return;
        setExplorer(next);
        setSelectedNode(next.nodes[0] ?? null);
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

  useEffect(() => {
    let cancelled = false;
    api.tasteDnaCompare("rolling_year", "this_month")
      .then((next) => {
        if (!cancelled) setComparison(next);
      })
      .catch(() => {
        if (!cancelled) setComparison(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const fallbackCore = dna?.core_dna?.length ? dna.core_dna.join(" / ") : interpretation?.core_genre_families?.map((item) => item.name).join(" / ");
  const months = explorer?.period.available_months ?? [];
  const nodes = explorer?.nodes ?? [];
  const traits = explorer?.traits ?? [];
  const activeNode = selectedNode ?? nodes[0] ?? null;
  const activeTrait = selectedTrait ?? traits[0] ?? null;
  const maxShare = useMemo(() => Math.max(...nodes.map((node) => node.share), 1), [nodes]);

  if (!dna && !interpretation && !explorer) return null;

  return (
    <section className="rounded-lg border border-line bg-panel/82 p-5 shadow-glow">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.18em] text-violet-200">Taste DNA Explorer</p>
          <h2 className="mt-1 text-2xl font-black text-white">{explorer?.core_identity ?? fallbackCore ?? "Mapped listening core"}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
            Interactive music analysis from detected plays and curated genre mappings. This explains sound patterns, not personality or psychology.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 rounded-lg border border-white/10 bg-white/[0.03] p-2">
          <PeriodButton active={period === "this_month"} label="This Month" onClick={() => setPeriod("this_month")} />
          <PeriodButton active={period === "month"} label="Selected Month" onClick={() => setPeriod("month")} />
          <PeriodButton active={period === "rolling_year"} label="Rolling Year" onClick={() => setPeriod("rolling_year")} />
          {period === "month" ? (
            <select className="rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-white" value={selectedMonth ?? months[months.length - 1]?.value ?? ""} onChange={(event) => setSelectedMonth(event.target.value)}>
              {months.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
            </select>
          ) : null}
        </div>
      </div>

      {explorer?.sample_warning ? <p className="mt-4 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">{explorer.sample_warning}</p> : null}

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="relative min-h-[440px] overflow-hidden rounded-lg border border-white/10 bg-[radial-gradient(circle_at_center,rgba(139,92,246,0.24),transparent_34%),linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))]">
          <button
            className="absolute left-1/2 top-1/2 z-10 grid h-40 w-40 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-violet/40 bg-ink/88 p-5 text-center shadow-glow focus:outline-none focus:ring-2 focus:ring-violet"
            onClick={() => setSelectedNode(nodes[0] ?? null)}
          >
            <span>
              <span className="block text-xs uppercase tracking-[0.18em] text-violet-200">Core Identity</span>
              <span className="mt-2 block text-base font-black leading-6 text-white">{explorer?.core_identity ?? fallbackCore ?? "Mapped core"}</span>
            </span>
          </button>
          {nodes.map((node) => {
            const intensity = Math.max(0.22, node.share / maxShare);
            return (
              <button
                key={node.id}
                className={`absolute rounded-full border px-3 py-2 text-center text-xs font-semibold shadow-lg transition focus:outline-none focus:ring-2 focus:ring-violet ${activeNode?.id === node.id ? "border-white bg-violet text-white" : "border-white/15 bg-black/45 text-mist hover:border-violet/60 hover:text-white"}`}
                style={{
                  left: `${node.x}%`,
                  top: `${node.y}%`,
                  minWidth: node.size,
                  minHeight: Math.max(42, node.size * 0.58),
                  transform: "translate(-50%, -50%)",
                  boxShadow: `0 0 ${20 + node.share}px rgba(167,139,250,${intensity})`,
                }}
                onClick={() => setSelectedNode(node)}
              >
                <span className="block">{node.name}</span>
                <span className="block text-[11px] opacity-80">{node.share}% - {node.layer}</span>
              </button>
            );
          })}
        </div>

        <div className="space-y-4">
          <DetailPanel node={activeNode} />
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <h3 className="text-sm font-semibold text-white">Sonic-trait orbit</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {traits.map((trait) => (
                <button
                  key={trait.trait}
                  className={`rounded-full border px-3 py-1 text-sm ${activeTrait?.trait === trait.trait ? "border-violet bg-violet/30 text-white" : "border-white/10 text-mist hover:text-white"}`}
                  onClick={() => setSelectedTrait(trait)}
                >
                  {trait.trait}
                </button>
              ))}
            </div>
            {activeTrait ? <TraitDetail trait={activeTrait} /> : <p className="mt-3 text-sm text-mist">Trait evidence appears after a refresh with mapped artists.</p>}
          </div>
        </div>
      </div>

      {comparison ? (
        <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.03] p-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="font-semibold text-white">Compare Current Month vs Rolling Year</h3>
              <p className="mt-1 text-sm text-mist">{comparison.summary_sentence}</p>
            </div>
            {comparison.sample_warning ? <span className="rounded-full bg-amber-200/10 px-3 py-1 text-xs text-amber-100">{comparison.sample_warning}</span> : null}
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <CompareClaim label="Growing cluster" value={comparison.claims.growing_cluster ? `${comparison.claims.growing_cluster.name} +${comparison.claims.growing_cluster.delta}` : "No strong claim"} />
            <CompareClaim label="Declining cluster" value={comparison.claims.declining_cluster ? `${comparison.claims.declining_cluster.name} ${comparison.claims.declining_cluster.delta}` : "No strong claim"} />
            <CompareClaim label="New side interest" value={comparison.claims.new_side_interest?.name ?? "None detected"} />
            <CompareClaim label="Stable core" value={comparison.claims.stable_core_identity.join(", ") || "Still forming"} />
          </div>
        </div>
      ) : null}

      <div className="mt-5 grid gap-3 md:grid-cols-4">
        {(explorer?.structured_summary ?? []).map((section) => (
          <div key={section.label} className="rounded-md bg-white/[0.04] p-4">
            <h3 className="text-sm font-semibold text-white">{section.label}</h3>
            <div className="mt-2 space-y-1 text-sm text-mist">
              {section.items.length ? section.items.map((item) => <p key={item}>{item}</p>) : <p>Not enough evidence</p>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function PeriodButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className={`rounded-md px-3 py-2 text-sm font-semibold ${active ? "bg-violet text-white" : "text-mist hover:bg-white/10 hover:text-white"}`} onClick={onClick}>
      {label}
    </button>
  );
}

function DetailPanel({ node }: { node: TasteDnaNode | null }) {
  if (!node) return <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-mist">No cluster selected.</div>;
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-violet-200">{node.layer}</p>
          <h3 className="mt-1 text-xl font-black text-white">{node.name}</h3>
        </div>
        <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-mist">{node.share}% share</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-mist">{node.role}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <MiniList title="Detected minutes" items={[node.detected_minutes_formatted]} />
        <MiniList title="Confidence" items={[`${node.confidence}% genre coverage`]} />
        <MiniList title="Top artists" items={node.top_artists.map((item) => `${item.name} (${item.plays})`)} />
        <MiniList title="Top songs" items={node.top_songs.map((item) => `${item.name} (${item.plays})`)} />
        <MiniList title="Canonical genres" items={node.canonical_genres} />
        <MiniList title="Sonic traits" items={node.sonic_traits} />
      </div>
    </div>
  );
}

function TraitDetail({ trait }: { trait: TasteTraitNode }) {
  return (
    <div className="mt-4 rounded-md bg-black/20 p-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-mist">
        <span className="rounded-full bg-white/10 px-3 py-1">{trait.support_percent}% of classified listening</span>
        <span className="rounded-full bg-white/10 px-3 py-1">{trait.confidence} confidence</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-mist">{trait.explanation}</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <MiniList title="Supporting clusters" items={trait.supporting_clusters.map((item) => `${item.name} (${item.plays})`)} />
        <MiniList title="Supporting artists" items={trait.supporting_artists.map((item) => `${item.name} (${item.plays})`)} />
      </div>
    </div>
  );
}

function MiniList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-3">
      <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/70">{title}</h4>
      <div className="mt-2 space-y-1 text-sm text-mist">
        {items.length ? items.slice(0, 5).map((item) => <p key={item}>{item}</p>) : <p>Unavailable</p>}
      </div>
    </div>
  );
}

function CompareClaim({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-3">
      <p className="text-xs uppercase tracking-[0.14em] text-mist/60">{label}</p>
      <p className="mt-2 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
