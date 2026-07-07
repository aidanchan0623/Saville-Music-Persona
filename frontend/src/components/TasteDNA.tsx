import type { TasteDNA as TasteDNAType, TasteInterpretation } from "../types/api";

const ringPositions = [
  "left-1/2 top-4 -translate-x-1/2",
  "right-4 top-1/3",
  "right-10 bottom-8",
  "left-10 bottom-8",
  "left-4 top-1/3",
  "left-1/2 bottom-4 -translate-x-1/2",
];

interface Props {
  dna: TasteDNAType | null | undefined;
  interpretation?: TasteInterpretation | null;
}

export function TasteDNA({ dna, interpretation }: Props) {
  if (!dna) return null;
  const core = dna.core_dna?.length ? dna.core_dna : interpretation?.core_genre_families?.map((item) => item.name) ?? [];
  const orbit = [...(dna.secondary_influences ?? []), ...(dna.sonic_traits ?? [])].slice(0, 6);
  return (
    <section className="rounded-lg border border-line bg-panel/82 p-5">
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Taste DNA</h2>
          <p className="mt-1 text-sm text-mist">Interpretive, not psychological: the recurring musical building blocks in your listening.</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-mist">
          <span className="rounded-full border border-white/10 px-3 py-1">{dna.artist_concentration?.label}</span>
          <span className="rounded-full border border-white/10 px-3 py-1">{dna.exploration_vs_comfort?.label}</span>
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_0.72fr]">
        <div className="relative min-h-[360px] overflow-hidden rounded-lg border border-white/10 bg-[radial-gradient(circle_at_center,rgba(139,92,246,0.2),transparent_36%),linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02))]">
          <div className="absolute left-1/2 top-1/2 grid h-44 w-44 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-violet/40 bg-ink/80 p-5 text-center shadow-glow">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-violet-200">Core DNA</p>
              <p className="mt-2 text-lg font-black leading-6 text-white">{core.slice(0, 3).join(" / ") || "Mapped taste core"}</p>
            </div>
          </div>
          {orbit.map((item, index) => (
            <span
              key={`${item}-${index}`}
              className={`absolute ${ringPositions[index % ringPositions.length]} max-w-[11rem] rounded-full border border-white/10 bg-black/35 px-3 py-2 text-center text-xs font-medium text-mist backdrop-blur`}
            >
              {item}
            </span>
          ))}
        </div>
        <div className="space-y-3">
          <MiniList title="Core families" items={interpretation?.core_genre_families?.map((item) => `${item.name} ${item.share}%`) ?? []} />
          <MiniList title="Secondary influences" items={dna.secondary_influences ?? []} />
          <MiniList title="Sonic traits" items={dna.sonic_traits ?? []} />
          <div className="rounded-md bg-white/[0.04] p-4 text-sm leading-6 text-mist">{dna.era_preference}</div>
        </div>
      </div>
    </section>
  );
}

function MiniList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-4">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? (
          items.map((item) => (
            <span key={item} className="rounded-full border border-white/10 px-3 py-1 text-xs text-mist">
              {item}
            </span>
          ))
        ) : (
          <span className="text-xs text-mist/70">Not enough confident data</span>
        )}
      </div>
    </div>
  );
}
