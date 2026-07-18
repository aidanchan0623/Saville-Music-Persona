import type { TasteInterpretation } from "../../types/api";

interface Props {
  taste: TasteInterpretation;
}

export function TasteNarrativeSection({ taste }: Props) {
  const core = taste.core_genre_families.map((item) => item.name);
  const secondary = taste.secondary_genre_families.map((item) => item.name);
  const traits = taste.sonic_traits.slice(0, 8);

  return (
    <section className="grid gap-10 py-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-start">
      <div className="max-w-3xl">
        <p className="section-label">What Your Taste Sounds Like</p>
        <h2 className="mt-3 text-4xl font-black leading-tight text-white md:text-5xl">
          Emotion, atmosphere, and guitar pressure with a polished pop edge.
        </h2>
        <p className="mt-6 text-lg leading-9 text-mist">{taste.summary}</p>
        <p className="mt-5 text-base leading-8 text-mist/90">
          The profile is not random variety. It has a clear emotional alternative centre, then moves outward through heavier cathartic rock, anthemic pop crossover, atmospheric textures, and cinematic side colour.
        </p>
      </div>

      <div className="relative overflow-hidden rounded-lg border border-white/10 bg-[linear-gradient(145deg,rgba(255,255,255,0.07),rgba(255,255,255,0.025))] p-6">
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-red-500/20 blur-3xl" />
        <SoundList title="Core genres" items={core} accent="red" />
        <SoundList title="Secondary influences" items={secondary} accent="deep" />
        <SoundList title="Sonic traits" items={traits} accent="soft" />
        {taste.coverage.unknown_artist_coverage_percent > 30 ? (
          <p className="mt-6 rounded-xl border border-amber-200/10 bg-amber-200/10 p-4 text-sm leading-6 text-amber-100">
            Smaller artists still have partial genre coverage, so the clearest claims come from the dominant mapped artists.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function SoundList({ title, items, accent }: { title: string; items: string[]; accent: "red" | "deep" | "soft" }) {
  const accentClass = {
    red: "bg-red-500/15 text-red-100 border-red-400/20",
    deep: "bg-red-950/35 text-red-100 border-red-900/40",
    soft: "bg-white/[0.055] text-mist border-white/10",
  }[accent];
  return (
    <div className="relative mt-6 first:mt-0">
      <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-mist/70">{title}</h3>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.length ? (
          items.map((item) => (
            <span key={item} className={`rounded-full border px-3 py-1.5 text-sm ${accentClass}`}>
              {item}
            </span>
          ))
        ) : (
          <span className="text-sm text-mist/70">No confident signal yet</span>
        )}
      </div>
    </div>
  );
}
