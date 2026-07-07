import { ArrowUpRight, BarChart3, Disc3, Gauge, Sparkles } from "lucide-react";

interface Props {
  onOpenTop10: () => void;
  onOpenScores: () => void;
  onOpenPatterns: () => void;
  onOpenReport: () => void;
}

export function ExploreProfileSection({ onOpenTop10, onOpenScores, onOpenPatterns, onOpenReport }: Props) {
  const tiles = [
    {
      title: "Top 10",
      description: "See your monthly and rolling-year leaders.",
      icon: Disc3,
      action: onOpenTop10,
    },
    {
      title: "Scores",
      description: "Understand how replay-heavy, niche, and exploratory your taste is.",
      icon: Gauge,
      action: onOpenScores,
    },
    {
      title: "Patterns",
      description: "View listening minutes, monthly shifts, and play trends.",
      icon: BarChart3,
      action: onOpenPatterns,
    },
    {
      title: "Persona Report",
      description: "Read the full written interpretation of your music identity.",
      icon: Sparkles,
      action: onOpenReport,
    },
  ];

  return (
    <section className="py-4">
      <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-200">Explore the profile</p>
          <h2 className="mt-2 text-3xl font-black text-white">Go deeper into the signal.</h2>
        </div>
        <p className="max-w-lg text-sm leading-6 text-mist">The homepage gives the identity. These sections show the evidence behind it.</p>
      </div>
      <div className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 md:grid-cols-2 xl:grid-cols-4">
        {tiles.map((tile) => {
          const Icon = tile.icon;
          return (
            <button key={tile.title} className="group bg-ink/86 p-5 text-left transition hover:bg-panelSoft focus:outline-none focus:ring-2 focus:ring-violet" onClick={tile.action}>
              <div className="flex items-start justify-between gap-4">
                <span className="grid h-11 w-11 place-items-center rounded-full bg-violet/15 text-violet-100">
                  <Icon size={20} />
                </span>
                <ArrowUpRight className="text-mist transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white" size={18} />
              </div>
              <h3 className="mt-5 text-lg font-black text-white">{tile.title}</h3>
              <p className="mt-2 text-sm leading-6 text-mist">{tile.description}</p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
